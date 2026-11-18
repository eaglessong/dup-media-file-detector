"""Original disposable bytes; relocation tests never use private media."""
import io
import json
import os
from pathlib import Path
import tempfile
import sys
import unittest
from contextlib import contextmanager

from dup_media.move_fs import runtime, MoveError
from dup_media.relocate import Relocation
from dup_media.scan import DEFAULT_EXTENSIONS


def make_tree(root):
    root.mkdir()
    (root / 'nested').mkdir()
    (root / 'a.jpg').write_bytes(b'a' * 100)
    (root / 'nested/b.jpg').write_bytes(b'a' * 100)
    (root / 'unique.wav').write_bytes(b'u' * 50)
    (root / 'ignored.txt').write_bytes(b'a' * 100)


def tree(root):
    if not root.exists():
        return None
    result = {}
    for p in root.rglob('*'):
        if p.is_file():
            info = p.stat()
            result[str(p.relative_to(root))] = (p.read_bytes(), info.st_mode, info.st_uid,
                                               info.st_gid, info.st_mtime_ns)
    return result


LINUX_PARENT_CASES = (
    'source_append', 'source_immutable', 'destination_append',
    'destination_immutable', 'destination_nodump', 'destination_missing_nodump',
    'destination_project', 'destination_project_inherit',
    'journal_append', 'journal_nodump',
)


def namespace_snapshot(root):
    """Detect file/directory changes, excluding read-atime side effects."""
    entries = {}
    for path in [root, *root.rglob('*')]:
        s = path.stat()
        entries[str(path.relative_to(root))] = (
            s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid,
            s.st_size, s.st_mtime_ns, s.st_ctime_ns,
            path.read_bytes() if path.is_file() else None)
    return entries


@contextmanager
def linux_parent_policy_tree(case):
    """Real ext4 policies on synthetic trees; reset flags before fixture cleanup."""
    import array
    import errno
    import fcntl
    from contextlib import ExitStack
    from types import SimpleNamespace

    with ExitStack() as stack:
        base = Path(stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        source, dest, journal = base / 'source', base / 'dest', base / 'operation'
        make_tree(source)
        (source / 'c.jpg').write_bytes(b'second exact group')
        late = source / 'zz-blocked'
        late.mkdir()
        (late / 'second.jpg').write_bytes(b'second exact group')
        roots = [base]
        if case.startswith('destination_project'):
            cross = Path(stack.enter_context(tempfile.TemporaryDirectory(
                dir=os.environ['MOVE_CROSS_ROOT']))).resolve()
            assert cross.stat().st_dev != source.stat().st_dev
            roots.append(cross)
            dest = cross / 'dest'
        if case.startswith('source_'):
            parent = late
        elif case.startswith('destination_'):
            parent = dest / 'zz-blocked'
            parent.mkdir(parents=True)
            if case == 'destination_missing_nodump':
                # The nearest existing ancestor, with two absent descendants.
                dest = parent / 'missing' / 'destination'
        else:
            parent = base / 'journal-parent'
            parent.mkdir()
            journal = parent / 'operation'
        control = parent / 'control.txt'
        control.write_bytes(b'original synthetic policy control')
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            flags = array.array('I', [0])
            fcntl.ioctl(fd, 0x80086601, flags, True)
            original = flags[0]
            project = array.array('I', [0] * 7)
            fcntl.ioctl(fd, 0x801c581f, project, True)
            original_project = array.array('I', project)
            try:
                if 'project' in case:
                    project[3] = 123
                    if case.endswith('_inherit'):
                        project[0] |= 0x200  # FS_XFLAG_PROJINHERIT
                    fcntl.ioctl(fd, 0x401c5820, project, True)
                    actual = array.array('I', [0] * 7)
                    fcntl.ioctl(fd, 0x801c581f, actual, True)
                    assert actual[3] == 123
                    if case.endswith('_inherit'):
                        probe = parent / 'inherited-control.txt'
                        probe.write_bytes(b'project inheritance control')
                        probe_fd = os.open(probe, os.O_RDONLY)
                        try:
                            fcntl.ioctl(probe_fd, 0x801c581f, actual, True)
                            assert actual[3] == 123, 'native project inheritance required'
                        finally:
                            os.close(probe_fd)
                        probe.unlink()
                else:
                    bit = (0x20 if case.endswith('_append') else
                           0x10 if case.endswith('_immutable') else 0x40)
                    flags[0] = original | bit
                    fcntl.ioctl(fd, 0x40086602, flags, True)
                    fcntl.ioctl(fd, 0x80086601, flags, True)
                    assert flags[0] & bit, 'native directory flag required'
                    if bit in (0x10, 0x20):
                        # Native unlink control proves denial, even for root.
                        try:
                            control.unlink()
                        except OSError as exc:
                            assert exc.errno == errno.EPERM, exc
                        else:
                            raise AssertionError('directory policy must deny unlink')
                        if bit == 0x20:
                            assert os.access(parent, os.W_OK | os.X_OK,
                                             effective_ids=True)
                kind = 'source' if case.startswith('source_') else 'journal' if case.startswith('journal_') else 'destination'
                error = kind + ('_directory_project_unsupported' if case == 'destination_project'
                                else '_directory_flags_unsupported')

                def run(dry):
                    out = io.StringIO()
                    code = Relocation(source, dest, None if dry else journal).run(
                        DEFAULT_EXTENSIONS, out, dry)
                    return code, [json.loads(s) for s in out.getvalue().splitlines()]

                yield SimpleNamespace(source=source, dest=dest, journal=journal,
                                      snapshot=lambda: [namespace_snapshot(r) for r in roots],
                                      run=run, error=error)
            finally:
                # Source append/immutable prevents TemporaryDirectory cleanup.
                flags[0] = original
                fcntl.ioctl(fd, 0x40086602, flags, True)
                fcntl.ioctl(fd, 0x401c5820, original_project, True)
        finally:
            os.close(fd)


class MoveFixture(unittest.TestCase):
    def setUp(self):
        if not sys.platform.startswith('linux'):
            self.skipTest('strict Linux adapter fixture')
        try:
            runtime()
        except MoveError:
            if os.environ.get('REQUIRE_MOVE_TESTS') == '1':
                raise
            self.skipTest('privileged Linux metadata adapter required')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'source'
        self.dest = self.base / 'dest'
        self.journal = self.base / 'operation'
        make_tree(self.source)

    def run_move(self, dry=False):
        out = io.StringIO()
        code = Relocation(self.source, self.dest, None if dry else self.journal).run(DEFAULT_EXTENSIONS, out, dry)
        return code, [json.loads(s) for s in out.getvalue().splitlines()]
