"""Original synthetic bytes; tests selection and size, not media decoding."""
from pathlib import Path
import stat

BASE_SUMMARY = {'media_file_count': 3, 'total_size_bytes': 250, 'complete': True}


def make_media(root):
    root = Path(root)
    (root / 'nested').mkdir()
    for name, data in [('a.jpg', b'a' * 100), ('nested/雪.PNG', b'a' * 100),
                       ('unique.wav', b'b' * 50), ('ignored.txt', b'c' * 75)]:
        (root / name).write_bytes(data)


def snapshot(root):
    """Record names, types, bytes and symlink targets, without following links."""
    result = {}
    for path in Path(root).rglob('*'):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            value = ('link', str(path.readlink()))
        elif stat.S_ISREG(mode):
            value = ('file', path.read_bytes())
        else:
            value = ('other', stat.S_IFMT(mode))
        result[str(path.relative_to(root))] = value
    return result
