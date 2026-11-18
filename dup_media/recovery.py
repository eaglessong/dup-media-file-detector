"""Versioned owner-local recovery records; never deletion authority by themselves."""
import hashlib
import json
import os
import re
import sqlite3
import stat
import sys
import uuid
from urllib.parse import quote

from .scan import CHUNK, DIR_FLAGS, signature
from .move_fs import (Location, MoveError, identity, metadata, metadata_policy,
                      check_create, filesystem, attrs, sync_file)

CONTROL = '.dup-media-recovery'
MARKER = b'{"format":1}\n'
MAX_TEXT = 2 * 1024 * 1024
ITEM_COLUMNS = ('path', 'metadata', 'size', 'digest', 'signature', 'stage')
MANIFEST_SCHEMA = '''
CREATE TABLE operation(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE items(path TEXT PRIMARY KEY,metadata TEXT,size INTEGER,digest TEXT,
                   signature TEXT,stage TEXT);
'''
RECEIPT_SCHEMA = '''
CREATE TABLE operation(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE items(path TEXT PRIMARY KEY,size INTEGER,state TEXT,stage TEXT,
                   signature TEXT,digest TEXT,metadata TEXT);
'''


def fail(code='recovery_invalid', path='.'):
    raise MoveError(code, path)


def relative(path):
    if (not isinstance(path, str) or not path or len(path.encode('utf-8')) > 4096
            or '\x00' in path or any(p in ('', '.', '..') for p in path.split('/'))
            or path.split('/')[0] == CONTROL):
        fail()
    return path


def opaque(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value):
        fail()
    return value


def digest(stream):
    stream.seek(0)
    result = hashlib.sha256()
    while block := stream.read(CHUNK):
        result.update(block)
    return result.hexdigest()


def bounded_json(value):
    if not isinstance(value, str) or len(value.encode('utf-8')) > MAX_TEXT:
        fail()
    try:
        return json.loads(value)
    except (ValueError, RecursionError):
        fail()


def private(fd, directory=False, legacy=False):
    s = os.fstat(fd)
    if (s.st_uid != os.geteuid() or (not legacy and s.st_mode & 0o077)
            or not (stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode))):
        fail('recovery_permissions')
    filesystem(fd)
    attrs(fd)


def open_parent(path):
    location = Location(os.path.dirname(path))
    fd = location.open()
    return location, fd


class Database:
    """Pin a plain database and reject mutable sidecars on read-only input."""
    def __init__(self, path, *, create=False, legacy=False):
        self.path = os.path.abspath(path)
        self.parent, parent = open_parent(self.path)
        self.fd = None
        self.db = None
        self.writable = create
        self.legacy = legacy
        try:
            private(parent, directory=True)
            leaf = os.path.basename(self.path)
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL if create else os.O_RDONLY
            self.fd = os.open(leaf, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=parent)
            private(self.fd, legacy=legacy)
            for suffix in ('-wal', '-shm', '-journal'):
                try:
                    os.stat(leaf + suffix, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    fail('recovery_sidecar')
            self.initial = signature(os.fstat(self.fd))
            # Linux procfd pins the file itself; Darwin checks ordinary path identity
            # before/after SQLite use. Exclusive namespaces remain a precondition.
            target = self.path if sys.platform == 'darwin' else f'/proc/self/fd/{self.fd}'
            uri = 'file:' + quote(target, safe='/') + ('?mode=rw' if create else '?mode=ro&immutable=1')
            self.db = sqlite3.connect(uri, uri=True)
            if hasattr(self.db, 'enable_load_extension'):
                self.db.enable_load_extension(False)
            self.db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_TEXT + 8192)
            self.db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 64)
            self.db.execute('PRAGMA trusted_schema=OFF')
            self.db.execute('PRAGMA cache_size=-2048')
            if create:
                self.db.execute('PRAGMA synchronous=FULL')
                if sys.platform == 'darwin':
                    self.db.execute('PRAGMA fullfsync=ON')
                    if self.db.execute('PRAGMA fullfsync').fetchone()[0] != 1:
                        fail('journal_sync_unsupported')
            self.check()
        except BaseException:
            self.close()
            raise
        finally:
            os.close(parent)

    def check(self):
        parent = self.parent.open()
        try:
            s = os.stat(os.path.basename(self.path), dir_fd=parent, follow_symlinks=False)
            if (s.st_dev, s.st_ino) != identity(self.fd):
                fail('recovery_changed')
            if not self.writable and signature(s) != self.initial:
                fail('recovery_changed')
        finally:
            os.close(parent)

    def schema(self, expected):
        objects = self.db.execute("SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
        found = {}
        for name, kind, sql in objects:
            if kind != 'table' or not sql or not sql.upper().startswith('CREATE TABLE '):
                fail()
            if name not in expected:
                fail()
            found[name] = tuple(x[1] for x in self.db.execute('PRAGMA table_info(' + name + ')'))
        if found != expected:
            fail()

    def values(self):
        result = {}
        for key, value in self.db.execute('SELECT key,value FROM operation'):
            if key in result or key not in {'version', 'id', 'policy', 'original', 'source_id',
                                           'archive_id', 'state', 'count'}:
                fail()
            result[key] = bounded_json(value)
        if set(result) != {'version', 'id', 'policy', 'original', 'source_id', 'archive_id', 'state', 'count'}:
            fail()
        if type(result['version']) is not int or result['version'] != 1:
            fail('recovery_unsupported_version')
        opaque(result['id'])
        if result['policy'] != metadata_policy():
            fail('metadata_policy_mismatch')
        if result['state'] not in ('PENDING', 'COMPLETE', 'STARTED'):
            fail()
        if type(result['count']) is not int or result['count'] < 0:
            fail()
        for name in ('source_id', 'archive_id'):
            if (not isinstance(result[name], list) or len(result[name]) != 2
                    or any(type(v) is not int or v < 0 for v in result[name])):
                fail()
        original = result['original']
        if (not isinstance(original, str) or not original.startswith('/') or '\x00' in original
                or len(original.encode('utf-8')) > 4096 or '..' in original.split('/')):
            fail()
        return result

    def set(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO operation VALUES (?,?)', (key, json.dumps(value)))

    def commit(self):
        self.check()
        self.db.commit()
        sync_file(self.fd)
        parent = self.parent.open()
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
        self.check()

    def close(self):
        try:
            if self.db is not None:
                self.db.close()
                self.db = None
        finally:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def directory(path, create=False):
    """Create at most one protected child of a pinned existing parent."""
    location, fd = open_parent(path)
    try:
        if create:
            check_create(fd, directories=True, kind='recovery')
            os.mkdir(os.path.basename(path), 0o700, dir_fd=fd)
            os.fsync(fd)
        child = os.open(os.path.basename(path), DIR_FLAGS, dir_fd=fd)
        try:
            private(child, directory=True)
        finally:
            os.close(child)
    finally:
        os.close(fd)
    return Location(path)


def control(archive):
    """Validate the reserved namespace without creating anything."""
    root = os.path.join(archive.path, CONTROL)
    if not os.path.lexists(root):
        return None
    loc = directory(root)
    fd = loc.open()
    try:
        with os.scandir(fd) as entries:
            for entry in entries:
                if entry.name not in ('format.json', 'operations'):
                    fail('recovery_control_collision')
        marker = os.open('format.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            private(marker)
            if os.read(marker, 1024) != MARKER:
                fail('recovery_unsupported_version')
        finally:
            os.close(marker)
    finally:
        os.close(fd)
    directory(os.path.join(root, 'operations'))
    return root


def operations(archive):
    root = control(archive)
    if root is None:
        return
    location = Location(os.path.join(root, 'operations'))
    fd = location.open()
    try:
        with os.scandir(fd) as entries:
            for entry in entries:
                opaque(entry.name)
                op = os.path.join(location.path, entry.name)
                directory(op)
                yield entry.name, op
    finally:
        os.close(fd)


def preflight_control(archive, rows):
    for row in rows:
        relative(row[0])  # Also reserves CONTROL in the destination mapping.
        if len(row[3].encode('utf-8')) > MAX_TEXT:
            fail('recovery_record_too_large', row[0])
    root = control(archive)
    if root:
        parent = Location(os.path.join(root, 'operations')).open()
        try:
            check_create(parent, directories=True, kind='recovery')
        finally:
            os.close(parent)
        for name, op in operations(archive):
            with Database(os.path.join(op, 'manifest.sqlite')) as record:
                record.schema({'operation': ('key', 'value'), 'items': ITEM_COLUMNS})
                values = record.values()
                if values['id'] != name or values['archive_id'] != list(archive.pins[-1]):
                    fail()
                if values['state'] != 'COMPLETE':
                    fail('operation_incomplete')
            receipt = os.path.join(op, 'revert', 'receipt.sqlite')
            if os.path.lexists(os.path.join(op, 'revert')):
                with Database(receipt) as record:
                    record.schema({'operation': ('key', 'value'), 'items':
                                   ('path', 'size', 'state', 'stage', 'signature', 'digest', 'metadata')})
                    if record.values()['state'] != 'COMPLETE':
                        fail('revert_incomplete')
    else:
        parent = archive.nearest()
        try:
            attrs(parent)
            check_create(parent, directories=True, kind='recovery')
        finally:
            os.close(parent)


class Manifest:
    def __init__(self, source, archive, scan):
        self.record = None
        try:
            root = os.path.join(archive.path, CONTROL)
            if not os.path.lexists(root):
                directory(root, create=True)
                parent = Location(root).open()
                try:
                    fd = os.open('format.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent)
                    try:
                        os.write(fd, MARKER)
                        sync_file(fd)
                    finally:
                        os.close(fd)
                    os.fsync(parent)
                finally:
                    os.close(parent)
                directory(os.path.join(root, 'operations'), create=True)
            else:
                control(archive)
            self.id = uuid.uuid4().hex
            self.path = os.path.join(root, 'operations', self.id)
            directory(self.path, create=True)
            self.record = Database(os.path.join(self.path, 'manifest.sqlite'), create=True)
            self.record.db.executescript(MANIFEST_SCHEMA)
            fd = source.open()
            dest = archive.open()
            try:
                if sys.platform == 'darwin':
                    from .move_darwin import physical
                    locator = physical(source)
                else:
                    locator = os.path.realpath(source.path)
                values = dict(version=1, id=self.id, policy=metadata_policy(),
                              original=locator, source_id=list(identity(fd)),
                              archive_id=list(identity(dest)), state='PENDING',
                              count=scan.db.execute('SELECT COUNT(*) FROM move_plan').fetchone()[0])
            finally:
                os.close(fd)
                os.close(dest)
            for key, value in values.items():
                self.record.set(key, value)
            for path, meta, size, hashed in scan.db.execute(
                    'SELECT p.path,p.metadata,p.size,f.digest FROM move_plan p JOIN files f ON p.path=f.path ORDER BY p.path'):
                if len(meta.encode('utf-8')) > MAX_TEXT:
                    fail('recovery_record_too_large', path)
                self.record.db.execute('INSERT INTO items VALUES (?,?,?,?,NULL,NULL)', (path, meta, size, hashed))
            self.record.commit()
        except BaseException:
            self.close()
            raise

    def complete(self, archive, source, journal):
        for root in (archive, source):
            fd = root.open()
            os.close(fd)
        for path, encoded, size, hashed in self.record.db.execute('SELECT path,metadata,size,digest FROM items ORDER BY path'):
            state, stage, dev, ino, error = journal.db.execute(
                'SELECT state,stage,dev,ino,error FROM items WHERE path=?', (path,)).fetchone()
            if state != 'source_removed' or error:
                fail('operation_incomplete', path)
            parent = Location(os.path.join(archive.path, os.path.dirname(path))).open()
            original = Location(os.path.join(source.path, os.path.dirname(path))).open()
            try:
                try:
                    os.stat(os.path.basename(path), dir_fd=original, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    fail('source_changed', path)
                try:
                    os.stat(stage, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    fail('staging_changed', path)
                fd = os.open(os.path.basename(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(fd, 'rb') as stream:
                    before = signature(os.fstat(fd))
                    if (identity(fd) != (int(dev), int(ino)) or before[2] != size
                            or metadata(fd) != bounded_json(encoded) or digest(stream) != hashed
                            or before != signature(os.fstat(fd))):
                        fail('destination_changed', path)
                    self.record.db.execute('UPDATE items SET signature=?,stage=? WHERE path=?',
                                           (json.dumps(before), stage, path))
            finally:
                os.close(parent)
                os.close(original)
        self.record.set('state', 'COMPLETE')
        self.record.commit()

    def close(self):
        if self.record is not None:
            self.record.close()
            self.record = None
