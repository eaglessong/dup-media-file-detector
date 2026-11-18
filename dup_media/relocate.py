"""Fresh exact-proof relocation with no-clobber publication and durable receipts."""
import fcntl
import json
import os
import sqlite3
import stat
import unicodedata
import uuid
from contextlib import contextmanager

from .scan import Scan, DIR_FLAGS, CHUNK, signature
from .move_fs import (Location, MoveError, absolute, overlap, runtime, filesystem,
                      mounts, attrs, metadata, apply_metadata, identity)
from .move_journal import Journal


def emit(output, **record):
    output.write(json.dumps(record, ensure_ascii=True) + '\n')
    output.flush()  # A broken consumer must be observed before any more removals.


def equal_streams(left, right):
    left.seek(0)
    right.seek(0)
    while True:
        a, b = left.read(CHUNK), right.read(CHUNK)
        if a != b:
            return False
        if not a:
            return True


def checkpoint(name, path):
    """Internal injection seam for boundary tests; no environment-triggered hooks."""


@contextmanager
def checked_source(scan, path):
    def expected():
        dev, ino, size, mtime, ctime = scan.db.execute(
            'SELECT dev,ino,size,mtime,ctime FROM files WHERE path=?', (path,)).fetchone()
        return int(dev), int(ino), size, mtime, ctime
    parent = scan.directory(path.rpartition('/')[0] or '.')
    try:
        fd = os.open(path.rsplit('/', 1)[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or signature(os.fstat(fd)) != expected():
            raise MoveError('source_changed', path)
        with os.fdopen(os.dup(fd), 'rb') as stream:
            yield stream
        # Only the controlled unlink may have refreshed indexed ctime for inode aliases.
        if signature(os.fstat(fd)) != expected():
            raise MoveError('source_changed', path)
    finally:
        os.close(fd)


class Relocation:
    def __init__(self, source, destination, journal=None):
        self.source = Location(source)
        self.destination = Location(destination)
        if self.source.existing != len(self.source.parts) or overlap(self.source, self.destination):
            raise ValueError('unsafe roots')
        self.journal_path = absolute(journal) if journal else None
        if journal:
            j = Location(journal)
            if overlap(j, self.source) or overlap(j, self.destination):
                raise ValueError('unsafe journal')
            if j.existing == len(j.parts) or j.existing != len(j.parts) - 1:
                raise ValueError('journal must be new with an existing parent')

    def rows(self, scan):
        return scan.db.execute('SELECT path,keeper,size,metadata FROM move_plan ORDER BY keeper,path')

    def dest_parent(self, scan, relative, create=False):
        """Walk pinned destination directories. Missing preflight parents stay missing."""
        fd = self.destination.open(create=create)
        prefix = ''
        try:
            for part in relative.split('/')[:-1]:
                prefix = part if not prefix else prefix + '/' + part
                row = scan.db.execute('SELECT dev,ino FROM move_dirs WHERE path=?', (prefix,)).fetchone()
                try:
                    child = os.open(part, DIR_FLAGS, dir_fd=fd)
                    if row is not None and row[0] is None:
                        os.close(child)
                        raise MoveError('destination_changed', relative)
                except FileNotFoundError:
                    if row is not None and row[0] is not None:
                        raise MoveError('destination_changed', relative)
                    if not create:
                        raise
                    os.mkdir(part, 0o700, dir_fd=fd)
                    os.fsync(fd)
                    child = os.open(part, DIR_FLAGS, dir_fd=fd)
                key = tuple(map(str, identity(child)))
                if row is not None and row[0] is not None and row != key:
                    os.close(child)
                    raise MoveError('destination_changed', relative)
                scan.db.execute('INSERT OR REPLACE INTO move_dirs VALUES (?,?,?)', (prefix, *key))
                os.close(fd)
                fd = child
                if attrs(fd):  # user.* on existing dirs is fine; attrs rejects ACLs.
                    pass
                if filesystem(fd) != self.dest_fs:
                    raise MoveError('destination_mount_changed', relative)
            return fd
        except BaseException:
            os.close(fd)
            raise

    def preflight(self, scan):
        scan.db.executescript('''
            CREATE TABLE move_plan(path TEXT PRIMARY KEY,keeper TEXT,size INTEGER,metadata TEXT);
            CREATE TABLE move_dirs(path TEXT PRIMARY KEY,dev TEXT,ino TEXT);
            CREATE TABLE move_names(folded TEXT PRIMARY KEY,path TEXT);
        ''')
        # Freeze every keeper before inserting victims; no digest/inode deduplication.
        for group, keeper in scan.db.execute('SELECT group_id,MIN(path) FROM files WHERE valid=1 AND group_id IS NOT NULL GROUP BY group_id HAVING COUNT(*)>1 ORDER BY MIN(path)'):
            with scan.source(keeper) as stream:
                metadata(stream.fileno())
            for path, size in scan.db.execute('SELECT path,size FROM files WHERE group_id=? AND valid=1 AND path<>? ORDER BY path', (group, keeper)):
                with scan.source(path) as stream:
                    meta = metadata(stream.fileno())
                scan.db.execute('INSERT INTO move_plan VALUES (?,?,?,?)', (path, keeper, size, json.dumps(meta, sort_keys=True)))
        nearest = self.destination.nearest()
        try:
            self.dest_fs = filesystem(nearest)
            attrs(nearest)  # Reject inherited ACL/security metadata before mutation.
            if os.fstatvfs(nearest).f_flag & os.ST_RDONLY:
                raise MoveError('destination_readonly')
            space = os.fstatvfs(nearest)
            available = space.f_bavail * space.f_frsize
            limit = os.fpathconf(nearest, 'PC_NAME_MAX')
        finally:
            os.close(nearest)
        total = 0
        for path, keeper, size, meta in self.rows(scan):
            total += size
            parts = path.split('/')
            for i, part in enumerate(parts, 1):
                if not part or part in ('.', '..') or len(os.fsencode(part)) > limit:
                    raise MoveError('unsupported_destination_name', path)
                prefix = '/'.join(parts[:i])
                key = unicodedata.normalize('NFC', prefix).casefold()
                old = scan.db.execute('SELECT path FROM move_names WHERE folded=?', (key,)).fetchone()
                if old and old[0] != prefix:
                    raise MoveError('destination_name_alias', path)
                scan.db.execute('INSERT OR IGNORE INTO move_names VALUES (?,?)', (key, prefix))
            # Record all missing parents even when the destination root doesn't exist.
            try:
                fd = self.dest_parent(scan, path)
            except FileNotFoundError:
                for i in range(1, len(parts)):
                    scan.db.execute('INSERT OR IGNORE INTO move_dirs VALUES (?,NULL,NULL)', ('/'.join(parts[:i]),))
            else:
                try:
                    try:
                        os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        raise MoveError('destination_exists', path)
                finally:
                    os.close(fd)
            parent = scan.directory(path.rpartition('/')[0] or '.')
            try:
                if os.fstatvfs(parent).f_flag & os.ST_RDONLY:
                    raise MoveError('source_readonly', path)
            finally:
                os.close(parent)
        if total > available:
            raise MoveError('insufficient_space')
        scan.db.commit()

    @contextmanager
    def target(self, scan, path):
        fd = self.dest_parent(scan, path, create=True)
        try:
            yield fd, path.rsplit('/', 1)[-1]
        finally:
            os.close(fd)

    def transfer(self, scan, journal, path, keeper, encoded):
        expected = json.loads(encoded)
        # Keep descriptors open for both exact-proof participants through source unlink.
        with checked_source(scan, keeper) as kept, checked_source(scan, path) as source:
            if metadata(source.fileno()) != expected or not equal_streams(kept, source):
                raise MoveError('source_changed', path)
            keep_meta = metadata(kept.fileno())
            checkpoint('before_copy', path)
            with self.target(scan, path) as (parent, name):
                stage = '.dup-media-stage-' + uuid.uuid4().hex
                journal.state(path, 'copying', stage=stage)
                fd = os.open(stage, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                # Staging is intentionally retained with its receipt after any failure.
                try:
                    stage_id = identity(fd)
                    journal.state(path, 'copying', stage=stage, info=stage_id)
                    with os.fdopen(os.dup(fd), 'r+b') as target:
                        source.seek(0)
                        while block := source.read(CHUNK):
                            target.write(block)
                        target.flush()
                        if not equal_streams(source, target) or not equal_streams(kept, target):
                            raise MoveError('copy_verification_failed', path)
                    apply_metadata(fd, expected)
                    os.fsync(fd)
                    journal.state(path, 'staged_verified', stage=stage, info=stage_id)
                    checkpoint('staged_verified', path)
                    # No replace: FileExistsError leaves the victim and prior target intact.
                    os.link(stage, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                    os.fsync(parent)
                    checkpoint('published', path)
                    final = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                    try:
                        with os.fdopen(os.dup(final), 'rb') as destination:
                            if identity(final) != stage_id or not equal_streams(source, destination):
                                raise MoveError('destination_changed', path)
                        if metadata(final) != expected:
                            raise MoveError('metadata_verification_failed', path)
                    finally:
                        os.close(final)
                    # Reprove both indexed files after transfer and before committing removal intent.
                    if metadata(source.fileno()) != expected or metadata(kept.fileno()) != keep_meta:
                        raise MoveError('source_changed', path)
                    with checked_source(scan, path), checked_source(scan, keeper):
                        pass
                    if not equal_streams(kept, source):
                        raise MoveError('source_changed', path)
                    journal.state(path, 'destination_verified', stage=stage, info=stage_id)
                    checkpoint('before_unlink', path)
                    # Output flushing is coordinated by caller before each transfer.
                    source_parent = scan.directory(path.rpartition('/')[0] or '.')
                    try:
                        leaf = path.rsplit('/', 1)[-1]
                        if signature(os.stat(leaf, dir_fd=source_parent, follow_symlinks=False)) != signature(os.fstat(source.fileno())):
                            raise MoveError('source_changed', path)
                        # Recheck keeper and destination name immediately before destructive step.
                        with checked_source(scan, keeper):
                            pass
                        if identity(fd) != (os.stat(name, dir_fd=parent, follow_symlinks=False).st_dev,
                                            os.stat(name, dir_fd=parent, follow_symlinks=False).st_ino):
                            raise MoveError('destination_changed', path)
                        os.unlink(leaf, dir_fd=source_parent)
                        os.fsync(source_parent)
                    finally:
                        os.close(source_parent)
                    # Update only self-induced ctime for known aliases after the controlled unlink.
                    info = os.fstat(source.fileno())
                    scan.db.execute('UPDATE files SET ctime=? WHERE dev=? AND ino=?',
                                    (info.st_ctime_ns, str(info.st_dev), str(info.st_ino)))
                    journal.state(path, 'source_removed', stage=stage, info=stage_id)
                    checkpoint('source_removed', path)
                    if identity(fd) != (os.stat(stage, dir_fd=parent, follow_symlinks=False).st_dev,
                                        os.stat(stage, dir_fd=parent, follow_symlinks=False).st_ino):
                        raise MoveError('staging_changed', path)
                    os.unlink(stage, dir_fd=parent)
                    os.fsync(parent)
                finally:
                    os.close(fd)

    def run(self, extensions, output, dry_run):
        # Invalid overlapping roots have already failed before this capability/scan work.
        runtime()
        mounts([self.source, self.destination])
        if self.journal_path:
            mounts([Location(self.journal_path)])
        emit(output, schema_version=1, type='header', operation='move_duplicates', dry_run=dry_run)
        moved = byte_count = count = errors = 0
        current = '.'
        journal = None
        with Scan(self.source.path, extensions) as scan:
            source_lock = dest_lock = None
            try:
                if not dry_run:
                    fcntl.flock(scan.root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    source_lock = scan.root_fd
                    dest_lock = self.destination.nearest()
                    fcntl.flock(dest_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                scan.run()
                if scan.db.execute('SELECT 1 FROM errors LIMIT 1').fetchone():
                    for path, code in scan.db.execute('SELECT DISTINCT path,code FROM errors ORDER BY path,code'):
                        emit(output, type='error', source=path, code=code)
                    raise MoveError('incomplete_scan')
                filesystem(scan.root_fd)
                self.preflight(scan)
                if self.journal_path:
                    jf = Location(os.path.dirname(self.journal_path)).open()
                    try:
                        attrs(jf)
                        filesystem(jf)
                        if os.fstatvfs(jf).f_flag & os.ST_RDONLY:
                            raise MoveError('journal_readonly')
                    finally:
                        os.close(jf)
                count = scan.db.execute('SELECT COUNT(*) FROM move_plan').fetchone()[0]
                checkpoint('preflight_complete', '.')
                if not dry_run and count:
                    dest_fd = self.destination.open(create=True)
                    try:
                        journal = Journal(self.journal_path, scan.root_fd, dest_fd, self.rows(scan))
                    finally:
                        os.close(dest_fd)
                for path, keeper, size, meta in self.rows(scan):
                    current = path
                    emit(output, type='item', keeper=keeper, source=path, destination=path,
                         size_bytes=size, status='planned')
                    if not dry_run:
                        self.transfer(scan, journal, path, keeper, meta)
                        moved += 1
                        byte_count += size
                        emit(output, type='item', keeper=keeper, source=path, destination=path,
                             size_bytes=size, status='moved')
            except (OSError, ValueError, sqlite3.Error) as exc:
                if isinstance(exc, BrokenPipeError):
                    raise
                errors += 1
                code = getattr(exc, 'code', 'io_failure')
                path = getattr(exc, 'path', current)
                emit(output, type='error', source=path, code=code)
            finally:
                if journal:
                    moved = byte_count = 0
                    for (size,) in journal.db.execute("SELECT size FROM items WHERE state='source_removed'"):
                        moved += 1
                        byte_count += size
                    journal.close()
                if dest_lock is not None:
                    os.close(dest_lock)
                if source_lock is not None:
                    fcntl.flock(source_lock, fcntl.LOCK_UN)
        emit(output, type='summary', complete=not errors, planned=count, moved=moved,
             bytes_moved=byte_count, errors=errors)
        return 1 if errors else 0
