import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dup_media.scan import Scan
from tests.summary_fixtures import BASE_SUMMARY, make_media, snapshot


class SummaryIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def report(self, **kwargs):
        with Scan(self.root, **kwargs) as scan:
            scan.run()
            output = io.StringIO()
            code = scan.write(output)
            return code, json.loads(output.getvalue())

    def test_all_media_including_unique_and_hardlinked_paths(self):
        make_media(self.root)
        before = snapshot(self.root)
        code, report = self.report()
        self.assertEqual(code, 0)
        self.assertEqual(report['summary'], BASE_SUMMARY)
        self.assertEqual(len(report['groups']), 1)
        self.assertEqual(report['groups'][0]['total_bytes'], 200)
        self.assertEqual(snapshot(self.root), before)
        os.link(self.root / 'a.jpg', self.root / 'hard.jpg')
        before = snapshot(self.root)
        code, report = self.report()
        self.assertEqual(code, 0)
        self.assertEqual(report['summary'], dict(BASE_SUMMARY, media_file_count=4, total_size_bytes=350))
        files = {f['path']: f['storage_id'] for f in report['groups'][0]['files']}
        self.assertEqual(files['a.jpg'], files['hard.jpg'])
        self.assertEqual(snapshot(self.root), before)

    def test_empty_ignored_and_zero_byte_files(self):
        for name, count in [(None, 0), ('ignored.txt', 0), ('empty.JPG', 1), ('empty.mp4', 2)]:
            if name:
                (self.root / name).touch()
            with self.subTest(name=name):
                code, report = self.report()
                self.assertEqual(code, 0)
                self.assertEqual(report['summary'], {'media_file_count': count, 'total_size_bytes': 0, 'complete': True})

    def test_override_and_skipped_links_special_files(self):
        make_media(self.root)
        (self.root / 'internal.jpg').symlink_to('a.jpg')
        (self.root / 'loop').symlink_to(self.root, target_is_directory=True)
        os.mkfifo(self.root / 'fifo.jpg')
        with tempfile.TemporaryDirectory() as external:
            Path(external, 'outside.jpg').write_bytes(b'z' * 900)
            (self.root / 'outside').symlink_to(external, target_is_directory=True)
            (self.root / 'outside.jpg').symlink_to(Path(external, 'outside.jpg'))
            before = snapshot(self.root)
            self.assertEqual(self.report()[1]['summary'], BASE_SUMMARY)
            code, report = self.report(extensions={'txt'})
            self.assertEqual(code, 0)
            self.assertEqual(report['summary'], {'media_file_count': 1, 'total_size_bytes': 75, 'complete': True})
            self.assertEqual(snapshot(self.root), before)
            self.assertEqual(Path(external, 'outside.jpg').read_bytes(), b'z' * 900)

    def test_mutated_unique_file_excluded_after_final_validation(self):
        make_media(self.root)
        original = Scan.enumerate
        expected_after_mutation = {}
        def mutate(scan):
            original(scan)
            (self.root / 'unique.wav').write_bytes(b'changed-size')
            expected_after_mutation.update(snapshot(self.root))
        with patch.object(Scan, 'enumerate', mutate):
            code, report = self.report()
        self.assertEqual(code, 1)
        self.assertFalse(report['complete'])
        self.assertEqual(report['summary'], {'media_file_count': 2, 'total_size_bytes': 200, 'complete': False})
        self.assertIn({'path': 'unique.wav', 'code': 'file_changed'}, report['errors'])
        self.assertEqual(snapshot(self.root), expected_after_mutation)

    def test_all_files_invalidated_remain_excluded_after_recovery(self):
        (self.root / 'a.jpg').write_bytes(b'abc')
        (self.root / 'b.jpg').write_bytes(b'abc')
        before = snapshot(self.root)
        # Controlled I/O failure: real files remain readable, but prior invalidation
        # must exclude them even though a later open would succeed.
        with patch.object(Scan, 'digest', side_effect=PermissionError('synthetic fault')):
            code, report = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(report['summary'], {'media_file_count': 0, 'total_size_bytes': 0, 'complete': False})
        self.assertEqual(len(report['errors']), 2)
        self.assertEqual(snapshot(self.root), before)

    @unittest.skipIf(os.geteuid() == 0, 'root bypasses POSIX permissions')
    def test_real_unreadable_file_and_directory(self):
        make_media(self.root)
        locked = self.root / 'locked'
        locked.mkdir()
        (locked / 'hidden.jpg').write_bytes(b'hidden')
        before = snapshot(self.root)
        (self.root / 'unique.wav').chmod(0)
        locked.chmod(0)
        try:
            code, report = self.report()
            self.assertEqual(code, 1)
            self.assertFalse(report['complete'])
            self.assertEqual(report['summary'], {'media_file_count': 2, 'total_size_bytes': 200, 'complete': False})
            self.assertIn({'path': 'unique.wav', 'code': 'read_failed'}, report['errors'])
            self.assertIn({'path': 'locked', 'code': 'directory_unreadable_or_changed'}, report['errors'])
        finally:
            (self.root / 'unique.wav').chmod(0o600)
            locked.chmod(0o700)
        self.assertEqual(snapshot(self.root), before)

    @unittest.skipIf(os.geteuid() == 0, 'root bypasses POSIX permissions')
    def test_unreadable_directory_is_not_empty_success(self):
        locked = self.root / 'locked'
        locked.mkdir()
        locked.chmod(0)
        try:
            code, report = self.report()
            self.assertEqual(code, 1)
            self.assertFalse(report['complete'])
            self.assertEqual(report['summary'], {'media_file_count': 0, 'total_size_bytes': 0, 'complete': False})
            self.assertTrue(report['errors'])
        finally:
            locked.chmod(0o700)

    def test_directory_added_after_enumeration_is_partial(self):
        make_media(self.root)
        original = Scan.enumerate
        def add(scan):
            original(scan)
            (self.root / 'late.jpg').write_bytes(b'late')
        with patch.object(Scan, 'enumerate', add):
            code, report = self.report()
        self.assertEqual(code, 1)
        self.assertFalse(report['complete'])
        self.assertEqual(report['summary'], dict(BASE_SUMMARY, complete=False))
        self.assertTrue(report['errors'])

    def test_sparse_logical_sizes_and_summary_do_not_read_sources(self):
        sizes = [2**32 + 1, 2**32 + 2]
        for index, size in enumerate(sizes):
            with (self.root / f'{index}.mp4').open('wb') as stream:
                stream.truncate(size)
        with Scan(self.root) as scan:
            with patch.object(scan, 'digest', side_effect=AssertionError('unique sizes must not hash')):
                scan.run()
            with patch.object(scan, 'source', side_effect=AssertionError('summary must not open sources')):
                output = io.StringIO()
                self.assertEqual(scan.write(output), 0)
            self.assertEqual(json.loads(output.getvalue())['summary'], {'media_file_count': 2, 'total_size_bytes': sum(sizes), 'complete': True})
