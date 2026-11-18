"""Conservative Linux relocation filesystem adapter; scanning does not depend on it."""
import array
import ctypes
import fcntl
import os
from pathlib import Path
import stat
import struct
import sys

from .scan import DIR_FLAGS


class MoveError(OSError):
    def __init__(self, code, path='.'):
        super().__init__(code)
        self.code, self.path = code, path


def identity(fd):
    s = os.fstat(fd)
    return s.st_dev, s.st_ino


def absolute(path):
    if '..' in Path(path).parts:
        raise ValueError('unsafe path')
    return os.path.abspath(path)


class Location:
    """Pin existing root ancestors without creating a missing suffix."""
    def __init__(self, path):
        self.path = absolute(path)
        self.parts = Path(self.path).parts[1:]
        self.pins = []
        fd = os.open('/', DIR_FLAGS)
        try:
            self.pins.append(identity(fd))
            for part in self.parts:
                try:
                    child = os.open(part, DIR_FLAGS, dir_fd=fd)
                except FileNotFoundError:
                    break
                os.close(fd)
                fd = child
                self.pins.append(identity(fd))
            self.existing = len(self.pins) - 1
            self.device = os.fstat(fd).st_dev
        finally:
            os.close(fd)

    def open(self, create=False):
        fd = os.open('/', DIR_FLAGS)
        try:
            if identity(fd) != self.pins[0]:
                raise MoveError('root_changed')
            for i, part in enumerate(self.parts, 1):
                try:
                    child = os.open(part, DIR_FLAGS, dir_fd=fd)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(part, 0o700, dir_fd=fd)
                    os.fsync(fd)
                    child = os.open(part, DIR_FLAGS, dir_fd=fd)
                if i < len(self.pins):
                    if identity(child) != self.pins[i]:
                        os.close(child)
                        raise MoveError('root_changed')
                elif create:
                    self.pins.append(identity(child))
                os.close(fd)
                fd = child
            return fd
        except BaseException:
            os.close(fd)
            raise

    def nearest(self):
        fd = os.open('/', DIR_FLAGS)
        try:
            for i, part in enumerate(self.parts[:self.existing], 1):
                child = os.open(part, DIR_FLAGS, dir_fd=fd)
                if identity(child) != self.pins[i]:
                    os.close(child)
                    raise MoveError('root_changed')
                os.close(fd)
                fd = child
            return fd
        except BaseException:
            os.close(fd)
            raise


def overlap(a, b):
    common = os.path.commonpath([a.path, b.path])
    if common in (a.path, b.path):
        return True
    # An existing root may also appear under another spelling/mount ancestry.
    return ((a.existing == len(a.parts) and a.pins[-1] in b.pins)
            or (b.existing == len(b.parts) and b.pins[-1] in a.pins))


def runtime():
    if sys.platform == 'darwin' and ctypes.sizeof(ctypes.c_void_p) == 8:
        return
    if not sys.platform.startswith('linux') or ctypes.sizeof(ctypes.c_void_p) != 8 or os.geteuid() != 0:
        raise MoveError('unsupported_metadata_runtime')
    with open('/proc/self/status', encoding='ascii') as stream:
        caps = next(int(s.split()[1], 16) for s in stream if s.startswith('CapEff:'))
    required = (1 << 0) | (1 << 1) | (1 << 3) | (1 << 21)
    if caps & required != required:
        raise MoveError('metadata_capabilities_required')


def filesystem(fd):
    libc = ctypes.CDLL(None, use_errno=True)
    buf = ctypes.create_string_buffer(256)
    if libc.fstatfs(fd, buf) != 0:
        raise MoveError('filesystem_probe_failed')
    kind = struct.unpack_from('@l', buf)[0]
    if kind != 0xEF53:
        raise MoveError('unsupported_filesystem')
    return kind


def mount_records():
    with open('/proc/self/mountinfo', encoding='utf-8') as stream:
        for line in stream:
            fields = line.split()
            def decode(value):
                for code, char in [('040', ' '), ('011', '\t'), ('012', '\n'), ('134', '\\')]:
                    value = value.replace('\\' + code, char)
                return value
            yield fields[2], decode(fields[3]), decode(fields[4])


def mount_location(location, records):
    candidates = [(len(point), device, root, point) for device, root, point in records
                  if os.path.commonpath([point, location.path]) == point]
    if not candidates:
        raise MoveError('mount_probe_failed')
    _, device, root, point = max(candidates)
    return device, os.path.normpath(os.path.join(root, os.path.relpath(location.path, point)))


def mounts(locations):
    """Reject subordinate mountpoints and overlapping bind-mount spellings."""
    records = list(mount_records())  # Bounded by mount count, not media file count.
    for location in locations:
        if any(point.startswith(location.path.rstrip('/') + '/') for _, _, point in records):
            raise MoveError('nested_mount_unsupported')
    resolved = [mount_location(location, records) for location in locations]
    for i, (device, path) in enumerate(resolved):
        for other_device, other_path in resolved[i + 1:]:
            if device == other_device and os.path.commonpath([path, other_path]) in (path, other_path):
                raise ValueError('overlapping mount roots')


def scratch_outside(scratch, trees):
    records = list(mount_records())
    scratch_device, scratch_path = mount_location(Location(scratch), records)
    for tree in trees:
        device, path = mount_location(tree, records)
        if device == scratch_device and os.path.commonpath([path, scratch_path]) == path:
            raise ValueError('scratch aliases selected tree')


def attrs(fd):
    result = {}
    for key in os.listxattr(fd):
        if not key.startswith('user.'):
            raise MoveError('unsupported_metadata')
        result[key] = os.getxattr(fd, key).hex()
    return result


def metadata(fd):
    kind = filesystem(fd)
    libc = ctypes.CDLL(None, use_errno=True)
    buf = ctypes.create_string_buffer(256)
    if not hasattr(libc, 'statx'):
        raise MoveError('statx_unavailable')
    # statx(fd, "", AT_EMPTY_PATH, STATX_BASIC_STATS, buf).
    if libc.statx(fd, b'', 0x1000, 0x7ff, buf) != 0:
        raise MoveError('metadata_probe_failed')
    attributes = struct.unpack_from('@Q', buf, 8)[0]
    if attributes:
        raise MoveError('unsupported_inode_attributes')
    if kind == 0xEF53:
        flags = array.array('I', [0])
        fcntl.ioctl(fd, 0x80086601, flags, True)  # FS_IOC_GETFLAGS
        if flags[0] & ~0x80000:  # EXTENTS is storage layout, not copied metadata.
            raise MoveError('unsupported_inode_flags')
    project = array.array('I', [0] * 7)  # struct fsxattr, FS_IOC_FSGETXATTR
    fcntl.ioctl(fd, 0x801c581f, project, True)
    # nextents is storage allocation, not transferred metadata. Reject unsupported
    # project IDs, xflags and extent-size policy rather than silently discarding them.
    if project[0] or project[1] or project[3] or project[4]:
        raise MoveError('unsupported_project_metadata')
    s = os.fstat(fd)
    if not stat.S_ISREG(s.st_mode) or s.st_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
        raise MoveError('unsupported_file_mode')
    return dict(uid=s.st_uid, gid=s.st_gid, mode=stat.S_IMODE(s.st_mode),
                mtime=s.st_mtime_ns, xattrs=attrs(fd))


def apply_metadata(fd, expected):
    os.fchown(fd, expected['uid'], expected['gid'])
    for key in os.listxattr(fd):
        if key not in expected['xattrs']:
            raise MoveError('inherited_metadata')
    for key, value in expected['xattrs'].items():
        os.setxattr(fd, key, bytes.fromhex(value))
    os.fchmod(fd, expected['mode'])
    os.utime(fd, ns=(os.fstat(fd).st_atime_ns, expected['mtime']))
    if metadata(fd) != expected:
        raise MoveError('metadata_verification_failed')


def sync_file(fd):
    os.fsync(fd)


def metadata_policy():
    return 'macos-data-only' if sys.platform == 'darwin' else 'linux-strict'


def check_delete(fd, leaf, path):
    if not os.access('.', os.W_OK | os.X_OK, dir_fd=fd, effective_ids=True):
        raise MoveError('source_permission_denied', path)
    parent = os.fstat(fd)
    if parent.st_mode & stat.S_ISVTX and os.geteuid() not in (0, parent.st_uid):
        victim = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
        if os.geteuid() != victim.st_uid:
            raise MoveError('source_permission_denied', path)


def check_create(fd, directories=False, kind='destination', path='.'):
    if not os.access('.', os.W_OK | os.X_OK, dir_fd=fd, effective_ids=True):
        raise MoveError(kind + '_permission_denied', path)


# Isolate Darwin contracts; retain strict Linux implementations unchanged above.
if sys.platform == 'darwin':
    from .move_darwin import (filesystem, mounts, scratch_outside, attrs, metadata,
                              apply_metadata, sync_file, check_delete, check_create)
