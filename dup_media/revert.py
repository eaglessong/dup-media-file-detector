"""Completed-operation restoration with fresh proofs and no automatic partial resume."""
import fcntl
import json
import os
import re
import sqlite3
import stat
import unicodedata
import uuid
from contextlib import ExitStack, contextmanager

from .scan import Scan, DIR_FLAGS, signature
from .move_fs import (Location, MoveError, identity, overlap, runtime, mounts,
                      scratch_outside, filesystem, metadata, metadata_policy,
                      check_create, check_delete, apply_metadata, sync_file, attrs)
from .relocate import emit, copy_stream, equal_streams
from .recovery import (CONTROL, Database, ITEM_COLUMNS, RECEIPT_SCHEMA, bounded_json,
                       digest, directory, fail, opaque, operations, relative)


def checkpoint(name, path):
    """Observation seam for tests, never environment-driven execution."""


def absent(fd, leaf, code, path):
    try:
        os.stat(leaf, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    fail(code, path)


class Revert:
    def __init__(self, archive, original=None, move_journal=None, operation=None):
        self.archive = Location(archive)
        if self.archive.existing != len(self.archive.parts):
            raise ValueError('archive unavailable')
        self.original_arg, self.journal_arg, self.operation = original, move_journal, opaque(operation) if operation else None
        self.scratch = os.path.realpath(os.environ.get('TMPDIR') or os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp')
        self.inputs = []
        self.legacy = False
        self.already = False
        self.receipt = None

    def input(self, stack, path, legacy=False):
        db = stack.enter_context(Database(path, legacy=legacy))
        self.inputs.append(db)
        return db

    def discover(self, stack, output):
        entries = 0
        chosen = None
        for name, op in operations(self.archive):
            entries += 1
            with Database(os.path.join(op, 'manifest.sqlite')) as record:
                record.schema({'operation': ('key', 'value'), 'items': ITEM_COLUMNS})
                values = record.values()
                if values['id'] != name or values['archive_id'] != list(self.archive.pins[-1]):
                    fail('root_identity_mismatch')
                if values['state'] != 'COMPLETE':
                    fail('operation_incomplete')
            # Refuse unresolved operations even with an explicit selector: v1 does
            # not try to prove isolation from partially completed recovery work.
            if os.path.lexists(os.path.join(op, 'revert')):
                with Database(os.path.join(op, 'revert', 'receipt.sqlite')) as receipt:
                    receipt.schema({'operation': ('key', 'value'), 'items':
                                    ('path', 'size', 'state', 'stage', 'signature', 'digest', 'metadata')})
                    if receipt.values()['state'] != 'COMPLETE':
                        fail('revert_incomplete')
            if self.operation is None or name == self.operation:
                chosen = op
        if entries:
            if self.original_arg or self.journal_arg:
                fail('recovery_argument_conflict')
            if self.operation is None and entries != 1:
                for name, _ in operations(self.archive):
                    emit(output, type='available_operation', operation_id=name)
                fail('recovery_ambiguous')
            if chosen is None:
                fail('recovery_missing')
            record = self.input(stack, os.path.join(chosen, 'manifest.sqlite'))
            record.schema({'operation': ('key', 'value'), 'items': ITEM_COLUMNS})
            self.values = record.values()
            self.rows = record.db.execute('SELECT path,metadata,size,digest,signature,stage FROM items')
            self.receipt_path = os.path.join(chosen, 'revert')
            self.original = Location(self.values['original'])
        else:
            # A present control tree with no operations is not permission to fall
            # back from new metadata to arbitrary legacy input.
            if os.path.lexists(os.path.join(self.archive.path, CONTROL)):
                fail('recovery_missing')
            if not self.original_arg or not self.journal_arg or self.operation:
                fail('recovery_missing')
            self.legacy = True
            self.original = Location(self.original_arg)
            self.legacy_journal = Location(self.journal_arg)
            if (overlap(self.legacy_journal, self.original)
                    or overlap(self.legacy_journal, self.archive)):
                fail('unsafe_journal')
            record = self.input(stack, os.path.join(self.legacy_journal.path, 'journal.sqlite'), legacy=True)
            record.schema({'roots': ('kind', 'dev', 'ino'), 'items':
                           ('path', 'keeper', 'size', 'metadata', 'state', 'stage', 'dev', 'ino',
                            'error', 'source_signature', 'keeper_signature', 'sha256')})
            roots = {}
            for kind, dev, ino in record.db.execute('SELECT kind,dev,ino FROM roots'):
                if kind not in ('source', 'destination') or kind in roots:
                    fail()
                roots[kind] = [int(dev), int(ino)]
            if set(roots) != {'source', 'destination'}:
                fail()
            self.values = dict(version=1, id=uuid.uuid5(uuid.NAMESPACE_OID, str(identity(record.fd))).hex,
                               policy=metadata_policy(), original=self.original.path,
                               source_id=roots['source'], archive_id=roots['destination'], state='COMPLETE',
                               count=record.db.execute('SELECT COUNT(*) FROM items').fetchone()[0])
            def legacy_rows(record=record):
                for path, encoded, size, hashed, stage, dev, ino, state, error in record.db.execute(
                        'SELECT path,metadata,size,sha256,stage,dev,ino,state,error FROM items'):
                    if state != 'source_removed' or error:
                        fail('operation_incomplete')
                    yield path, encoded, size, hashed, json.dumps([int(dev), int(ino), size]), stage
            self.rows = legacy_rows()
            self.receipt_path = os.path.join(self.legacy_journal.path, 'revert')
        if (self.original.existing != len(self.original.parts) or overlap(self.original, self.archive)
                or list(self.original.pins[-1]) != self.values['source_id']
                or list(self.archive.pins[-1]) != self.values['archive_id']):
            fail('root_identity_mismatch')
        if os.path.lexists(self.receipt_path):
            record = self.input(stack, os.path.join(self.receipt_path, 'receipt.sqlite'))
            record.schema({'operation': ('key', 'value'), 'items':
                           ('path', 'size', 'state', 'stage', 'signature', 'digest', 'metadata')})
            values = record.values()
            if values['state'] != 'COMPLETE':
                fail('revert_incomplete')
            if any(values[k] != self.values[k] for k in self.values if k != 'state'):
                fail()
            self.already = True
            self.completed_receipt = record

    def original_directory(self, scan, path):
        fd = self.original.open()
        try:
            if path != '.':
                for i, part in enumerate(path.split('/'), 1):
                    child = os.open(part, DIR_FLAGS, dir_fd=fd)
                    os.close(fd)
                    fd = child
                    prefix = '/'.join(path.split('/')[:i])
                    expected = scan.db.execute('SELECT dev,ino FROM restore_dirs WHERE path=?', (prefix,)).fetchone()
                    if expected is not None and tuple(map(str, identity(fd))) != expected:
                        fail('root_changed', path)
            return fd
        except BaseException:
            os.close(fd)
            raise

    def directories(self, scan):
        scan.db.execute('INSERT INTO dirs(path,dev,ino) VALUES (?,?,?)', ('.', *map(str, identity(scan.root_fd))))
        original = self.original.open()
        try:
            scan.db.execute('INSERT INTO restore_dirs VALUES (?,?,?)', ('.', *map(str, identity(original))))
        finally:
            os.close(original)
        while row := scan.db.execute('SELECT path FROM dirs WHERE done=0 ORDER BY path LIMIT 1').fetchone():
            path = row[0]
            parent = scan.directory(path)
            try:
                try:
                    target = self.original_directory(scan, path)
                except OSError:
                    fail('structure_mismatch', path)
                try:
                    if filesystem(parent) != filesystem(scan.root_fd) or filesystem(target) != filesystem(scan.root_fd):
                        fail('nested_mount_unsupported', path)
                    scan.db.execute('INSERT OR REPLACE INTO restore_dirs VALUES (?,?,?)',
                                    (path, *map(str, identity(target))))
                finally:
                    os.close(target)
                with os.scandir(parent) as entries:
                    for entry in entries:
                        if path == '.' and entry.name == CONTROL and not self.legacy:
                            continue
                        name = entry.name if path == '.' else path + '/' + entry.name
                        relative(name)
                        info = entry.stat(follow_symlinks=False)
                        if stat.S_ISLNK(info.st_mode):
                            fail('unsafe_archive_entry', name)
                        if stat.S_ISDIR(info.st_mode):
                            scan.db.execute('INSERT INTO dirs(path,dev,ino) VALUES (?,?,?)',
                                            (name, str(info.st_dev), str(info.st_ino)))
                scan.db.execute('UPDATE dirs SET done=1 WHERE path=?', (path,))
            finally:
                os.close(parent)

    def checks(self):
        for record in self.inputs:
            record.check()
        for root in (self.archive, self.original):
            fd = root.open()
            os.close(fd)

    @contextmanager
    def archive_file(self, scan, path):
        parent = scan.directory(os.path.dirname(path) or '.')
        try:
            fd = os.open(os.path.basename(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        finally:
            os.close(parent)
        try:
            row = scan.db.execute('SELECT signature FROM restore_plan WHERE path=?', (path,)).fetchone()
            if (not stat.S_ISREG(os.fstat(fd).st_mode)
                    or list(signature(os.fstat(fd))) != bounded_json(row[0])):
                fail('archive_changed', path)
            with os.fdopen(os.dup(fd), 'rb') as stream:
                yield stream
            latest = scan.db.execute('SELECT signature FROM restore_plan WHERE path=?', (path,)).fetchone()[0]
            if list(signature(os.fstat(fd))) != bounded_json(latest):
                fail('archive_changed', path)
        finally:
            os.close(fd)

    def plan(self, scan):
        scan.db.executescript('''
            CREATE TABLE restore_plan(path TEXT PRIMARY KEY,metadata TEXT,size INTEGER,digest TEXT,signature TEXT,stage TEXT,dev TEXT,ino TEXT);
            CREATE INDEX restore_inodes ON restore_plan(dev,ino);
            CREATE TABLE restore_dirs(path TEXT PRIMARY KEY,dev TEXT,ino TEXT);
            CREATE TABLE restore_names(folded TEXT PRIMARY KEY,path TEXT);
        ''')
        self.directories(scan)
        count, total = 0, 0
        for path, encoded, size, hashed, sig, stage in self.rows:
            relative(path)
            expected = bounded_json(sig)
            meta = bounded_json(encoded)
            if (type(size) is not int or size < 0 or not isinstance(meta, dict)
                    or not isinstance(hashed, str) or not re.fullmatch('[a-f0-9]{64}', hashed)
                    or not isinstance(expected, list) or len(expected) != (3 if self.legacy else 5)
                    or any(type(n) is not int for n in expected) or expected[2] != size
                    or not isinstance(stage, str) or not re.fullmatch(r'\.dup-media-stage-[a-f0-9]{32}', stage)):
                fail()
            # Validate target aliases including shared directory prefixes on disk.
            parts = path.split('/')
            for i in range(1, len(parts)+1):
                prefix = '/'.join(parts[:i]); key = unicodedata.normalize('NFC', prefix).casefold()
                old = scan.db.execute('SELECT path FROM restore_names WHERE folded=?', (key,)).fetchone()
                if old and old[0] != prefix:
                    fail('restore_name_alias', path)
                scan.db.execute('INSERT OR IGNORE INTO restore_names VALUES (?,?)', (key, prefix))
            count += 1; total += size
            scan.db.execute('INSERT INTO restore_plan VALUES (?,?,?,?,?,?,?,?)',
                            (path, encoded, size, hashed, sig, stage, str(expected[0]), str(expected[1])))
        if count != self.values['count'] or count == 0:
            fail('recovery_invalid')
        if self.already:
            self.check_completed(scan)
            return
        for path, encoded, size, hashed, sig, stage in self.rows_for(scan):
            parent = scan.directory(os.path.dirname(path) or '.')
            target = None
            try:
                target = self.original_directory(scan, os.path.dirname(path) or '.')
                absent(parent, stage, 'operation_incomplete', path)
                absent(target, os.path.basename(path), 'restore_target_exists', path)
                attrs(target)
                check_create(target, path=path)
                check_delete(parent, os.path.basename(path), path)
                if os.fstatvfs(parent).f_flag & os.ST_RDONLY or os.fstatvfs(target).f_flag & os.ST_RDONLY:
                    fail('readonly_filesystem', path)
                if len(os.fsencode(os.path.basename(path))) > os.fpathconf(target, 'PC_NAME_MAX'):
                    fail('unsupported_destination_name', path)
                fd = os.open(os.path.basename(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(fd, 'rb') as stream:
                    before = signature(os.fstat(fd)); expected = bounded_json(sig)
                    if (not stat.S_ISREG(os.fstat(fd).st_mode) or list(before[:len(expected)]) != expected
                            or metadata(fd) != bounded_json(encoded) or digest(stream) != hashed
                            or before != signature(os.fstat(fd))):
                        fail('archive_changed', path)
                    scan.db.execute('UPDATE restore_plan SET signature=? WHERE path=?', (json.dumps(before), path))
            finally:
                os.close(parent)
                if target is not None:
                    os.close(target)
        parent = self.original.open()
        try:
            space = os.fstatvfs(parent)
            if total + 1024*1024 + count*4096 > space.f_bavail * space.f_frsize:
                fail('insufficient_space')
        finally:
            os.close(parent)
        receipt_parent = Location(os.path.dirname(self.receipt_path)).open()
        try:
            attrs(receipt_parent)
            check_create(receipt_parent, directories=True, kind='journal')
            if os.fstatvfs(receipt_parent).f_flag & os.ST_RDONLY:
                fail('journal_readonly')
        finally:
            os.close(receipt_parent)
        self.checks()
        scan.db.commit()

    def rows_for(self, scan):
        return scan.db.execute('SELECT path,metadata,size,digest,signature,stage FROM restore_plan ORDER BY path')

    def check_completed(self, scan):
        seen = 0
        for path, size, state, stage, sig, hashed, encoded in self.completed_receipt.db.execute(
                'SELECT path,size,state,stage,signature,digest,metadata FROM items'):
            relative(path)
            row = scan.db.execute('SELECT size,digest,metadata FROM restore_plan WHERE path=?', (path,)).fetchone()
            if row != (size, hashed, encoded) or state != 'restored' or not isinstance(stage, str) or not re.fullmatch(r'\.dup-media-restore-[a-f0-9]{32}', stage):
                fail()
            parent = self.original_directory(scan, os.path.dirname(path) or '.')
            archived = None
            try:
                archived = scan.directory(os.path.dirname(path) or '.')
                absent(archived, os.path.basename(path), 'revert_state_changed', path)
                absent(parent, stage, 'revert_incomplete', path)
                fd = os.open(os.path.basename(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(fd, 'rb') as stream:
                    before = signature(os.fstat(fd))
                    if (list(before) != bounded_json(sig) or metadata(fd) != bounded_json(encoded)
                            or digest(stream) != hashed or before != signature(os.fstat(fd))):
                        fail('revert_state_changed', path)
                seen += 1
            finally:
                os.close(parent)
                if archived is not None:
                    os.close(archived)
        if seen != self.values['count']:
            fail()
        self.checks()

    def start_receipt(self, scan):
        directory(self.receipt_path, create=True)
        self.receipt = Database(os.path.join(self.receipt_path, 'receipt.sqlite'), create=True)
        self.receipt.db.executescript(RECEIPT_SCHEMA)
        for key, value in self.values.items():
            self.receipt.set(key, 'STARTED' if key == 'state' else value)
        for path, encoded, size, hashed, sig, stage in self.rows_for(scan):
            self.receipt.db.execute('INSERT INTO items VALUES (?,?,?,NULL,NULL,?,?)',
                                    (path, size, 'planned', hashed, encoded))
        self.receipt.commit()

    def state(self, path, state, stage, sig=None):
        self.receipt.db.execute('UPDATE items SET state=?,stage=?,signature=? WHERE path=?',
                                (state, stage, json.dumps(sig) if sig else None, path))
        self.receipt.commit()

    def transfer(self, scan, path, encoded):
        self.checks()
        expected = bounded_json(encoded)
        parent = self.original_directory(scan, os.path.dirname(path) or '.')
        archived = None
        fd = None
        try:
            archived = scan.directory(os.path.dirname(path) or '.')
            leaf = os.path.basename(path)
            absent(parent, leaf, 'restore_target_exists', path)
            with self.archive_file(scan, path) as source:
                if metadata(source.fileno()) != expected:
                    fail('archive_changed', path)
                stage = '.dup-media-restore-' + uuid.uuid4().hex
                self.state(path, 'copying', stage)
                fd = os.open(stage, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                with os.fdopen(os.dup(fd), 'r+b') as target:
                    copy_stream(source, target)
                    if not equal_streams(source, target):
                        fail('copy_verification_failed', path)
                apply_metadata(fd, expected)
                sync_file(fd)
                self.state(path, 'staged_verified', stage)
                checkpoint('staged_verified', path)
                self.checks()
                current = self.original_directory(scan, os.path.dirname(path) or '.')
                try:
                    if identity(current) != identity(parent):
                        fail('root_changed', path)
                finally:
                    os.close(current)
                os.link(stage, leaf, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                os.fsync(parent); sync_file(fd)
                self.state(path, 'restore_verified', stage)
                checkpoint('published', path)
                checkpoint('before_unlink', path)
                self.checks()
                current = self.original_directory(scan, os.path.dirname(path) or '.')
                actual_parent = scan.directory(os.path.dirname(path) or '.')
                try:
                    if identity(current) != identity(parent) or identity(actual_parent) != identity(archived):
                        fail('root_changed', path)
                finally:
                    os.close(current); os.close(actual_parent)
                final = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                try:
                    restored_signature = signature(os.fstat(fd))
                    with self.archive_file(scan, path) as live, os.fdopen(os.dup(final), 'rb') as restored:
                        if (identity(final) != identity(fd) or metadata(final) != expected
                                or metadata(live.fileno()) != expected or not equal_streams(live, restored)
                                or signature(os.fstat(final)) != restored_signature
                                or list(signature(os.fstat(live.fileno()))) != bounded_json(scan.db.execute(
                                    'SELECT signature FROM restore_plan WHERE path=?', (path,)).fetchone()[0])
                                or signature(os.stat(leaf, dir_fd=parent, follow_symlinks=False)) != restored_signature
                                or signature(os.stat(leaf, dir_fd=archived, follow_symlinks=False)) != signature(os.fstat(live.fileno()))):
                            fail('archive_changed', path)
                        os.unlink(leaf, dir_fd=archived)
                        checkpoint('after_unlink', path)
                        os.fsync(archived)
                        info = os.fstat(live.fileno())
                        # Track only controlled ctime changes for archive hardlink aliases.
                        for other, sig in scan.db.execute('SELECT path,signature FROM restore_plan WHERE dev=? AND ino=?',
                                                          (str(info.st_dev), str(info.st_ino))):
                            value = bounded_json(sig)
                            if value[:2] == [info.st_dev, info.st_ino]:
                                value[4] = info.st_ctime_ns
                                scan.db.execute('UPDATE restore_plan SET signature=? WHERE path=?', (json.dumps(value), other))
                finally:
                    os.close(final)
                self.state(path, 'archive_removed', stage)
                checkpoint('archive_removed', path)
                if identity(fd) != (os.stat(stage, dir_fd=parent, follow_symlinks=False).st_dev,
                                    os.stat(stage, dir_fd=parent, follow_symlinks=False).st_ino):
                    fail('staging_changed', path)
                os.unlink(stage, dir_fd=parent)
                os.fsync(parent)
                self.state(path, 'restored', stage, signature(os.fstat(fd)))
        finally:
            if fd is not None:
                os.close(fd)
            os.close(parent)
            if archived is not None:
                os.close(archived)

    def run(self, output, dry_run):
        runtime()
        restored = byte_count = count = errors = 0
        header = False
        def heading():
            nonlocal header
            emit(output, type='header', schema_version=1, operation='revert_move',
                 operation_id=getattr(self, 'values', {}).get('id'), provenance='legacy-journal' if self.legacy else 'manifest-v1',
                 dry_run=dry_run, metadata_policy=metadata_policy())
            header = True
        try:
            with ExitStack() as stack:
                self.discover(stack, output)
                heading()
                roots = [self.archive, self.original]
                if self.legacy:
                    roots.append(self.legacy_journal)
                mounts(roots)
                scratch_outside(self.scratch, roots)
                with Scan(self.archive.path, frozenset(), scratch_dir=self.scratch, pin_sqlite_temp=True) as scan:
                    if identity(scan.root_fd) != self.archive.pins[-1]:
                        fail('root_changed')
                    if not dry_run:
                        for root in roots:
                            fd = root.open()
                            stack.callback(os.close, fd)
                            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.plan(scan)
                    count = self.values['count']
                    checkpoint('preflight_complete', '.')
                    self.checks()
                    if self.already:
                        emit(output, type='summary', complete=True, planned=0, restored=0,
                             bytes_restored=0, errors=0, reason='already_reverted')
                        return 0
                    if not dry_run:
                        self.start_receipt(scan)
                    for path, encoded, size, hashed, sig, stage in self.rows_for(scan):
                        emit(output, type='item', source=path, destination=path, size_bytes=size, status='planned')
                        if not dry_run:
                            self.transfer(scan, path, encoded)
                            restored += 1; byte_count += size
                            emit(output, type='item', source=path, destination=path, size_bytes=size, status='restored')
                    if self.receipt:
                        self.receipt.set('state', 'COMPLETE')
                        self.receipt.commit()
        except (OSError, ValueError, sqlite3.Error) as exc:
            if isinstance(exc, BrokenPipeError):
                raise
            errors = 1
            if not header:
                heading()
            emit(output, type='error', source=getattr(exc, 'path', '.'), code=getattr(exc, 'code', 'io_failure'))
        finally:
            if self.receipt:
                try:
                    restored = byte_count = 0
                    for (size,) in self.receipt.db.execute("SELECT size FROM items WHERE state IN ('archive_removed','restored')"):
                        restored += 1; byte_count += size
                finally:
                    self.receipt.close()
        emit(output, type='summary', complete=not errors, planned=count, restored=restored,
             bytes_restored=byte_count, errors=errors)
        return 1 if errors else 0
