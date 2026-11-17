import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[2]


class CliE2E(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'dup_media', *map(str, args)], cwd=REPO, capture_output=True, text=True, timeout=30)

    def test_actual_entry_point_and_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / 'nested').mkdir()
            for name, data in [('a.jpg', b'abc'), ('nested/b.PNG', b'abc'), ('c.jpg', b'xyz'), ('ignored.txt', b'abc')]:
                (root / name).write_bytes(data)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            result = self.cli(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report['complete'])
            self.assertEqual([[f['path'] for f in g['files']] for g in report['groups']], [['a.jpg', 'nested/b.PNG']])
            self.assertEqual(report['groups'][0]['size_bytes'], 3)
            self.assertEqual(result.stdout, self.cli(root).stdout)
            self.assertNotIn(str(root), result.stdout + result.stderr)
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_invalid_root_extensions_and_symlink_root(self):
        result = self.cli('/does-not-exist-private-path')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('/does-not-exist', result.stderr)
        self.assertEqual(result.stdout, '')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / 'link').symlink_to(root, target_is_directory=True)
            self.assertEqual(self.cli(root / 'link').returncode, 2)
            self.assertEqual(self.cli(root, '--extensions', '.jpg').returncode, 2)
            (root / 'a.bin').write_bytes(b'123')
            (root / 'b.bin').write_bytes(b'123')
            self.assertEqual(len(json.loads(self.cli(root, '--extensions', 'bin').stdout)['groups']), 1)

    @unittest.skipIf(os.geteuid() == 0, 'root bypasses POSIX mode restrictions')
    def test_actual_permission_error(self):
        with tempfile.TemporaryDirectory() as folder:
            locked = Path(folder, 'locked')
            locked.mkdir(); locked.chmod(0)
            try:
                result = self.cli(Path(folder).resolve())
                self.assertEqual(result.returncode, 1)
                self.assertFalse(json.loads(result.stdout)['complete'])
            finally:
                locked.chmod(0o700)

    def test_sigint_during_real_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            # Sparse files make scanning slow without allocating large fixtures.
            for name in ['a.mp4', 'b.mp4']:
                with (root / name).open('wb') as stream:
                    stream.truncate(4 * 1024**3)
            process = subprocess.Popen([sys.executable, '-m', 'dup_media', str(root)], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                time.sleep(0.3)
                self.assertIsNone(process.poll(), 'scan ended before cancellation')
                process.send_signal(signal.SIGINT)
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 130, stderr)
                self.assertEqual(stdout, '')
                self.assertIn('cancelled', stderr)
                self.assertEqual(sorted(p.name for p in root.iterdir()), ['a.mp4', 'b.mp4'])
                self.assertTrue(all(p.stat().st_size == 4 * 1024**3 for p in root.iterdir()))
            finally:
                if process.poll() is None:
                    process.kill(); process.communicate()


if __name__ == '__main__':
    unittest.main()
