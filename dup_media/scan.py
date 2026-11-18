"""Disk-backed scanning with descriptor-relative, no-follow source access."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
from contextlib import contextmanager

DEFAULT_EXTENSIONS = frozenset('jpg jpeg png gif bmp tif tiff webp heic heif avif raw cr2 cr3 nef arw dng mp4 m4v mov avi mkv mpg mpeg webm wmv mts m2ts 3gp mp3 m4a aac flac wav ogg opus wma aiff aif'.split())
CHUNK = 1024 * 1024
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def open_root(path):
    """Reject symlinks in every root component, even ancestors."""
    if '..' in Path(path).parts:
        raise ValueError('parent traversal is not supported in root paths')
    absolute = os.path.abspath(path)
    fd = os.open('/', DIR_FLAGS)
    try:
        for part in Path(absolute).parts[1:]:
            child = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


class Changed(OSError):
    """An indexed file no longer has the recorded identity and metadata."""


class SourceFailure(OSError):
    def __init__(self, path, cause):
        self.path = path
        self.changed = isinstance(cause, Changed)


class Scan:
    def __init__(self, root, extensions=DEFAULT_EXTENSIONS, scratch_dir=None, pin_sqlite_temp=False):
        self.root = root
        self.extensions = extensions
        self.scratch_dir = scratch_dir
        self.pin_sqlite_temp = pin_sqlite_temp
        self.previous_sqlite_temp = None

    def __enter__(self):
        self.root_fd = open_root(self.root)
        try:
            # Never create scratch artifacts anywhere inside the source tree.
            root = Path(self.root).resolve()
            scratch = self.scratch_dir if self.scratch_dir is not None else tempfile.gettempdir()
            if Path(scratch).resolve().is_relative_to(root):
                raise ValueError('scratch directory is inside selected root')
            self.temp = tempfile.TemporaryDirectory(prefix='dup-media-', dir=scratch)
            self.db = sqlite3.connect(os.path.join(self.temp.name, 'index.sqlite'))
            if self.pin_sqlite_temp:
                previous = self.db.execute('PRAGMA temp_store_directory').fetchone()
                self.previous_sqlite_temp = previous[0] if previous else ''
                quoted = self.temp.name.replace("'", "''")
                self.db.execute("PRAGMA temp_store_directory='" + quoted + "'")
                if self.db.execute('PRAGMA temp_store_directory').fetchone() != (self.temp.name,):
                    raise ValueError('SQLite temp directory cannot be pinned')
            self.db.executescript('''
                PRAGMA cache_size=-2048;
                PRAGMA temp_store=FILE;
                CREATE TABLE files(path TEXT PRIMARY KEY, dev TEXT, ino TEXT,
                    size INTEGER, mtime INTEGER, ctime INTEGER, digest TEXT,
                    group_id INTEGER, valid INTEGER DEFAULT 1);
                CREATE INDEX sizes ON files(size);
                CREATE TABLE dirs(path TEXT PRIMARY KEY, dev TEXT, ino TEXT, done INTEGER DEFAULT 0, mtime INTEGER, ctime INTEGER);
                CREATE INDEX pending_dirs ON dirs(done,path);
                CREATE INDEX directory_identity ON dirs(dev,ino);
                CREATE INDEX memberships ON files(group_id,valid,path);
                CREATE TABLE errors(path TEXT, code TEXT);
            ''')
            return self
        except BaseException:
            if hasattr(self, 'db'):
                self._close_index()
            os.close(self.root_fd)
            if hasattr(self, 'temp'):
                self.temp.cleanup()
            raise

    def _close_index(self):
        try:
            if self.previous_sqlite_temp is not None:
                quoted = self.previous_sqlite_temp.replace("'", "''")
                self.db.execute("PRAGMA temp_store_directory='" + quoted + "'")
        finally:
            self.db.close()

    def __exit__(self, *args):
        try:
            self._close_index()
        finally:
            self.temp.cleanup()
            os.close(self.root_fd)

    def error(self, path, code):
        self.db.execute('INSERT INTO errors VALUES (?,?)', (path.encode('utf-8', 'backslashreplace').decode('utf-8'), code))

    def directory(self, path):
        fd = os.dup(self.root_fd)
        try:
            if path != '.':
                for index, part in enumerate(path.split('/')):
                    child = os.open(part, DIR_FLAGS, dir_fd=fd)
                    os.close(fd)
                    fd = child
                    prefix = '/'.join(path.split('/')[:index + 1])
                    expected = self.db.execute('SELECT dev,ino FROM dirs WHERE path=?', (prefix,)).fetchone()
                    info = os.fstat(fd)
                    if expected is not None and (str(info.st_dev), str(info.st_ino)) != expected:
                        raise Changed()
            return fd
        except BaseException:
            os.close(fd)
            raise

    def enumerate(self):
        info = os.fstat(self.root_fd)
        self.db.execute('INSERT INTO dirs(path,dev,ino) VALUES (?,?,?)', ('.', str(info.st_dev), str(info.st_ino)))
        while True:
            row = self.db.execute('SELECT path,dev,ino FROM dirs WHERE done=0 LIMIT 1').fetchone()
            if row is None:
                break
            path, dev, ino = row
            self.db.execute('UPDATE dirs SET done=1 WHERE path=?', (path,))
            try:
                fd = self.directory(path)
                try:
                    before = os.fstat(fd)
                    if (str(before.st_dev), str(before.st_ino)) != (dev, ino):
                        raise Changed()
                    with os.scandir(fd) as entries:
                        for entry in entries:
                            relative = entry.name if path == '.' else path + '/' + entry.name
                            try:
                                try:
                                    relative.encode('utf-8')
                                except UnicodeEncodeError:
                                    self.error(relative, 'unsupported_filename_encoding')
                                    continue
                                info = entry.stat(follow_symlinks=False)
                                if stat.S_ISDIR(info.st_mode):
                                    if self.db.execute('SELECT 1 FROM dirs WHERE dev=? AND ino=?', (str(info.st_dev), str(info.st_ino))).fetchone():
                                        self.error(relative, 'directory_alias')
                                        continue
                                    self.db.execute('INSERT INTO dirs(path,dev,ino) VALUES (?,?,?)',
                                                    (relative, str(info.st_dev), str(info.st_ino)))
                                elif stat.S_ISREG(info.st_mode) and Path(entry.name).suffix[1:].lower() in self.extensions:
                                    self.db.execute('INSERT INTO files(path,dev,ino,size,mtime,ctime) VALUES (?,?,?,?,?,?)',
                                                    (relative, str(info.st_dev), str(info.st_ino), info.st_size, info.st_mtime_ns, info.st_ctime_ns))
                            except OSError:
                                self.error(relative, 'stat_failed')
                    after = os.fstat(fd)
                    self.db.execute('UPDATE dirs SET mtime=?,ctime=? WHERE path=?', (before.st_mtime_ns, before.st_ctime_ns, path))
                    if (before.st_mtime_ns, before.st_ctime_ns) != (after.st_mtime_ns, after.st_ctime_ns):
                        self.error(path, 'directory_changed')
                finally:
                    os.close(fd)
            except OSError:
                self.error(path, 'directory_unreadable_or_changed')
        self.db.commit()

    @contextmanager
    def source(self, path):
        try:
            with self._source(path) as stream:
                yield stream
        except SourceFailure:
            raise
        except OSError as exc:
            raise SourceFailure(path, exc) from None

    @contextmanager
    def _source(self, path):
        row = self.db.execute('SELECT dev,ino,size,mtime,ctime FROM files WHERE path=?', (path,)).fetchone()
        expected = (int(row[0]), int(row[1]), *row[2:])
        parent, _, name = path.rpartition('/')
        directory = self.directory(parent or '.')
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        finally:
            os.close(directory)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or signature(info) != expected:
                raise Changed()
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                yield stream
            if signature(os.fstat(fd)) != expected:
                raise Changed()
        finally:
            os.close(fd)

    def invalidate(self, path, exc):
        path = getattr(exc, 'path', path)
        self.db.execute('UPDATE files SET valid=0 WHERE path=?', (path,))
        self.error(path, 'file_changed' if (isinstance(exc, Changed) or getattr(exc, 'changed', False)) else 'read_failed')

    def digest(self, path):
        result = hashlib.sha256()
        with self.source(path) as stream:
            while block := stream.read(CHUNK):
                result.update(block)
        return result.hexdigest()

    def equal(self, left, right):
        try:
            with self.source(left) as a, self.source(right) as b:
                while True:
                    try:
                        x = a.read(CHUNK)
                    except OSError as exc:
                        raise SourceFailure(left, exc) from None
                    try:
                        y = b.read(CHUNK)
                    except OSError as exc:
                        raise SourceFailure(right, exc) from None
                    if x != y:
                        return False
                    if not x:
                        return True
        except OSError as exc:
            self.invalidate(getattr(exc, 'path', left), exc)
            return False

    def run(self):
        self.enumerate()
        for (path,) in self.db.execute('SELECT path FROM files WHERE size IN (SELECT size FROM files GROUP BY size HAVING COUNT(*)>1) ORDER BY path'):
            try:
                digest = self.digest(path)
                self.db.execute('UPDATE files SET digest=? WHERE path=?', (digest, path))
            except OSError as exc:
                self.invalidate(path, exc)
        self.db.execute('CREATE INDEX candidates ON files(size,digest,valid)')
        group_id = 0
        for size, digest in self.db.execute('SELECT size,digest FROM files WHERE valid=1 AND digest IS NOT NULL GROUP BY size,digest HAVING COUNT(*)>1 ORDER BY size,digest'):
            for (path,) in self.db.execute('SELECT path FROM files WHERE size=? AND digest=? AND valid=1 ORDER BY path', (size, digest)):
                assigned = False
                for representative, existing_id in self.db.execute('SELECT MIN(path),group_id FROM files WHERE size=? AND digest=? AND valid=1 AND group_id IS NOT NULL GROUP BY group_id', (size, digest)):
                    if self.equal(representative, path):
                        self.db.execute('UPDATE files SET group_id=? WHERE path=?', (existing_id, path))
                        assigned = True
                        break
                if not assigned:
                    group_id += 1
                    self.db.execute('UPDATE files SET group_id=? WHERE path=? AND valid=1', (group_id, path))
        for (path,) in self.db.execute('SELECT path FROM files WHERE valid=1 ORDER BY path'):
            try:
                with self.source(path):
                    pass
            except OSError as exc:
                self.invalidate(path, exc)
        # Revalidate directories, including replacements after enumeration.
        for path, dev, ino, mtime, ctime in self.db.execute('SELECT path,dev,ino,mtime,ctime FROM dirs'):
            try:
                fd = self.directory(path)
                try:
                    info = os.fstat(fd)
                    if (str(info.st_dev), str(info.st_ino)) != (dev, ino) or (info.st_mtime_ns, info.st_ctime_ns) != (mtime, ctime):
                        raise Changed()
                finally:
                    os.close(fd)
            except OSError:
                self.error(path, 'directory_unreadable_or_changed')
        self.db.commit()

    def _summary(self, complete):
        """Count logical bytes per validated path without SQLite SUM overflow."""
        count = total = 0
        for (size,) in self.db.execute('SELECT size FROM files WHERE valid=1'):
            count += 1
            total += size
        return {'media_file_count': count, 'total_size_bytes': total,
                'complete': complete}

    def write(self, output):
        complete = not self.db.execute('SELECT 1 FROM errors LIMIT 1').fetchone()
        summary = self._summary(complete)
        output.write('{"schema_version":1,"complete":' + ('true' if complete else 'false') + ',"summary":')
        json.dump(summary, output)
        output.write(',"groups":[')
        first = True
        for group_id, size, count in self.db.execute('SELECT group_id,size,COUNT(*) FROM files WHERE valid=1 AND group_id IS NOT NULL GROUP BY group_id HAVING COUNT(*)>1 ORDER BY MIN(path)'):
            if not first:
                output.write(',')
            first = False
            output.write('{"size_bytes":%d,"total_bytes":%d,"files":[' % (size, size * count))
            for index, (path, dev, ino) in enumerate(self.db.execute('SELECT path,dev,ino FROM files WHERE valid=1 AND group_id=? ORDER BY path', (group_id,))):
                if index:
                    output.write(',')
                json.dump({'path': path, 'storage_id': dev + ':' + ino}, output, ensure_ascii=True)
            output.write(']}')
        output.write('],"errors":[')
        for index, (path, code) in enumerate(self.db.execute('SELECT DISTINCT path,code FROM errors ORDER BY path,code')):
            if index:
                output.write(',')
            json.dump({'path': path, 'code': code}, output, ensure_ascii=True)
        output.write(']}\n')
        return 0 if complete else 1
