import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.summary_fixtures import BASE_SUMMARY, make_media, snapshot

REPO = Path(__file__).resolve().parents[2]


class SummaryCliE2E(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'dup_media', str(self.root), *args], cwd=REPO, capture_output=True, text=True, timeout=30)

    def report(self, expected_code=0, *args):
        result = self.cli(*args)
        self.assertEqual(result.returncode, expected_code, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertNotIn(str(self.root), result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report['complete'], report['summary']['complete'])
        self.assertIs(type(report['summary']['media_file_count']), int)
        self.assertIs(type(report['summary']['total_size_bytes']), int)
        return report

    def test_default_summary_unique_media_hardlinks_and_preservation(self):
        make_media(self.root)
        before = snapshot(self.root)
        report = self.report()
        self.assertEqual(report['summary'], BASE_SUMMARY)
        self.assertEqual(report['schema_version'], 1)
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['groups'][0]['total_bytes'], 200)
        self.assertEqual(self.cli().stdout, self.cli().stdout)
        self.assertEqual(snapshot(self.root), before)
        os.link(self.root / 'a.jpg', self.root / 'hard.jpg')
        before = snapshot(self.root)
        report = self.report()
        self.assertEqual(report['summary'], dict(BASE_SUMMARY, media_file_count=4, total_size_bytes=350))
        self.assertEqual(snapshot(self.root), before)

    def test_empty_ignored_zero_byte_and_extension_override(self):
        self.assertEqual(self.report()['summary'], {'media_file_count': 0, 'total_size_bytes': 0, 'complete': True})
        (self.root / 'ignored.txt').write_bytes(b'x' * 75)
        self.assertEqual(self.report()['summary']['media_file_count'], 0)
        (self.root / 'empty.JPG').touch()
        (self.root / 'empty.mp4').touch()
        self.assertEqual(self.report()['summary'], {'media_file_count': 2, 'total_size_bytes': 0, 'complete': True})
        self.assertEqual(self.report(0, '--extensions', 'txt')['summary'], {'media_file_count': 1, 'total_size_bytes': 75, 'complete': True})

    def test_symlinks_and_special_files_are_not_counted(self):
        make_media(self.root)
        os.mkfifo(self.root / 'pipe.jpg')
        (self.root / 'internal.jpg').symlink_to('a.jpg')
        (self.root / 'loop').symlink_to(self.root, target_is_directory=True)
        with tempfile.TemporaryDirectory() as outside:
            Path(outside, 'outside.jpg').write_bytes(b'o' * 1024)
            (self.root / 'outside').symlink_to(outside, target_is_directory=True)
            (self.root / 'outside.jpg').symlink_to(Path(outside, 'outside.jpg'))
            before = snapshot(self.root)
            self.assertEqual(self.report()['summary'], BASE_SUMMARY)
            self.assertEqual(snapshot(self.root), before)
            self.assertEqual(Path(outside, 'outside.jpg').read_bytes(), b'o' * 1024)

    @unittest.skipIf(os.geteuid() == 0, 'root bypasses POSIX permissions')
    def test_partial_summary_from_real_permission_failures(self):
        make_media(self.root)
        locked = self.root / 'locked'
        locked.mkdir()
        (locked / 'hidden.jpg').write_bytes(b'hidden')
        before = snapshot(self.root)
        (self.root / 'unique.wav').chmod(0)
        locked.chmod(0)
        try:
            report = self.report(1)
            self.assertEqual(report['summary'], {'media_file_count': 2, 'total_size_bytes': 200, 'complete': False})
            self.assertIn({'path': 'unique.wav', 'code': 'read_failed'}, report['errors'])
            self.assertIn({'path': 'locked', 'code': 'directory_unreadable_or_changed'}, report['errors'])
        finally:
            (self.root / 'unique.wav').chmod(0o600)
            locked.chmod(0o700)
        self.assertEqual(snapshot(self.root), before)

    def test_sparse_files_report_exact_logical_integer_size(self):
        sizes = [2**32 + 1, 2**32 + 2]
        for index, size in enumerate(sizes):
            with (self.root / f'{index}.mp4').open('wb') as stream:
                stream.truncate(size)
        report = self.report()
        self.assertEqual(report['summary'], {'media_file_count': 2, 'total_size_bytes': sum(sizes), 'complete': True})
        self.assertEqual([p.stat().st_size for p in sorted(self.root.iterdir())], sizes)

    @unittest.skipIf(os.geteuid() == 0, 'root bypasses POSIX permissions')
    def test_all_unreadable_files_and_error_only_directory_are_partial_zero(self):
        path = self.root / 'unreadable.jpg'
        path.write_bytes(b'original')
        path.chmod(0)
        try:
            report = self.report(1)
            self.assertEqual(report['summary'], {'media_file_count': 0, 'total_size_bytes': 0, 'complete': False})
            self.assertIn({'path': 'unreadable.jpg', 'code': 'read_failed'}, report['errors'])
        finally:
            path.chmod(0o600)
        self.assertEqual(path.read_bytes(), b'original')
        path.unlink()  # Fixture setup for the error-only-directory case.
        locked = self.root / 'locked'
        locked.mkdir()
        locked.chmod(0)
        try:
            report = self.report(1)
            self.assertEqual(report['summary'], {'media_file_count': 0, 'total_size_bytes': 0, 'complete': False})
            self.assertTrue(report['errors'])
        finally:
            locked.chmod(0o700)
