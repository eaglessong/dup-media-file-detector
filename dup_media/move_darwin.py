"""APFS data-stream-only relocation primitives (Darwin 64-bit ABI)."""
import ctypes
import fcntl
import os
import stat


class StatFS(ctypes.Structure):
    _fields_ = [('bsize', ctypes.c_uint32), ('iosize', ctypes.c_int32),
                *[(n, ctypes.c_uint64) for n in ('blocks', 'bfree', 'bavail', 'files', 'ffree')],
                ('fsid', ctypes.c_int32 * 2),
                *[(n, ctypes.c_uint32) for n in ('owner', 'type', 'flags', 'subtype')],
                ('fstype', ctypes.c_char * 16), ('mount', ctypes.c_char * 1024),
                ('device', ctypes.c_char * 1024), ('extended', ctypes.c_uint32),
                ('reserved', ctypes.c_uint32 * 7)]


def error(code):
    from .move_fs import MoveError
    raise MoveError(code)


def libc():
    return ctypes.CDLL(None, use_errno=True)


def filesystem(fd):
    info = StatFS()
    if libc().fstatfs64(fd, ctypes.byref(info)) != 0:
        error('filesystem_probe_failed')
    if info.fstype != b'apfs':
        error('unsupported_filesystem')
    return 'apfs'


def physical(location):
    fd = location.nearest()
    try:
        path = os.fsdecode(fcntl.fcntl(fd, 102, bytes(1024)).split(b'\0', 1)[0])
        return os.path.join(path, *location.parts[location.existing:])
    finally:
        os.close(fd)


def contains(parent, child):
    return os.path.commonpath([parent, child]) == parent


def mounts(locations):
    physicals = [physical(item) for item in locations]
    for i, path in enumerate(physicals):
        for other in physicals[i + 1:]:
            if contains(path, other) or contains(other, path):
                raise ValueError('overlapping physical roots')
    table = ctypes.POINTER(StatFS)()
    api = libc()
    getmounts = getattr(api, 'getmntinfo$INODE64', api.getmntinfo)
    count = getmounts(ctypes.byref(table), 2)  # MNT_NOWAIT
    if count <= 0:
        error('mount_probe_failed')
    from .move_fs import Location
    for i in range(count):
        point = physical(Location(os.fsdecode(table[i].mount)))
        if any(point != path and contains(path, point) for path in physicals):
            error('nested_mount_unsupported')


def scratch_outside(scratch, trees):
    from .move_fs import Location
    path = physical(Location(scratch))
    if any(contains(physical(tree), path) for tree in trees):
        raise ValueError('scratch aliases selected tree')


def attrs(fd):
    # Native descriptor API: Python's macOS builds need not expose os.listxattr.
    api = libc()
    api.flistxattr.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    api.flistxattr.restype = ctypes.c_ssize_t
    length = api.flistxattr(fd, None, 0, 0)
    if length < 0:
        error('metadata_probe_failed')
    if length > 1024 * 1024:
        error('metadata_list_too_large')
    data = ctypes.create_string_buffer(length)
    used = api.flistxattr(fd, data, length, 0)
    if used < 0 or used > length:
        error('metadata_probe_failed')
    if b'com.apple.ResourceFork' in data.raw[:used].split(b'\0'):
        error('resource_fork_unsupported')
    return {}


def metadata(fd):
    filesystem(fd)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        error('unsupported_file_mode')
    if info.st_flags:
        error('unsupported_inode_flags')
    attrs(fd)
    return {'policy': 'macos-data-only'}


def apply_metadata(fd, expected):
    # Intentionally do not transfer permissions/times/ownership/attached metadata.
    if metadata(fd) != expected:
        error('metadata_verification_failed')


def sync_file(fd):
    os.fsync(fd)
    fcntl.fcntl(fd, 51)  # F_FULLFSYNC; fail closed if storage cannot honor request.
