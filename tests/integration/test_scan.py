import io
import json
import os
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from dup_media.scan import Scan


class ScanIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def file(self, name, data=b'abc'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def report(self, extensions=None):
        with Scan(self.root, **({'extensions': extensions} if extensions else {})) as scan:
            scan.run()
            output = io.StringIO()
            code = scan.write(output)
            return code, json.loads(output.getvalue())

    def test_exact_unicode_empty_filter_hardlinks_and_preservation(self):
        self.file('a.JPG')
        self.file('nested/雪.png')
        os.link(self.root / 'a.JPG', self.root / 'hard.jpg')
        self.file('different.jpg', b'xyz')
        self.file('ignored.txt')
        self.file('empty.mp3', b'')
        self.file('nested/empty.wav', b'')
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        code, result = self.report()
        self.assertEqual(code, 0)
        groups = result['groups']
        self.assertEqual([[f['path'] for f in g['files']] for g in groups], [['a.JPG', 'hard.jpg', 'nested/雪.png'], ['empty.mp3', 'nested/empty.wav']])
        self.assertEqual(groups[0]['total_bytes'], 9)
        self.assertEqual(groups[0]['files'][0]['storage_id'], groups[0]['files'][1]['storage_id'])
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(result, self.report()[1])

    def test_symlinks_and_special_files_are_skipped(self):
        self.file('a.jpg')
        with tempfile.TemporaryDirectory() as external:
            Path(external, 'outside.jpg').write_bytes(b'abc')
            (self.root / 'escape').symlink_to(external, target_is_directory=True)
            (self.root / 'link.jpg').symlink_to(Path(external, 'outside.jpg'))
            (self.root / 'loop').symlink_to(self.root, target_is_directory=True)
            os.mkfifo(self.root / 'pipe.jpg')
            self.assertEqual(self.report()[1]['groups'], [])

    def test_extension_override(self):
        self.file('a.bin'); self.file('b.BIN')
        self.assertEqual(self.report()[1]['groups'], [])
        self.assertEqual(len(self.report({'bin'})[1]['groups']), 1)

    def test_hash_collision_does_not_prove_equality(self):
        self.file('a.jpg', b'abc'); self.file('b.jpg', b'xyz'); self.file('c.jpg', b'xyz')
        with patch.object(Scan, 'digest', return_value='collision'):
            groups = self.report()[1]['groups']
        self.assertEqual([[f['path'] for f in g['files']] for g in groups], [['b.jpg', 'c.jpg']])

    def test_changed_during_hash_is_incomplete(self):
        self.file('a.jpg'); self.file('b.jpg')
        original = Scan.digest
        def mutate(scan, path):
            digest = original(scan, path)
            if path == 'a.jpg':
                (self.root / path).write_bytes(b'new')
            return digest
        with patch.object(Scan, 'digest', mutate):
            code, result = self.report()
        self.assertEqual(code, 1)
        self.assertFalse(result['complete'])
        self.assertEqual(result['groups'], [])
        self.assertIn({'path': 'a.jpg', 'code': 'file_changed'}, result['errors'])

    def test_ancestor_replaced_with_symlink(self):
        self.file('nested/a.jpg'); self.file('b.jpg')
        with Scan(self.root) as scan:
            scan.enumerate()
            (self.root / 'nested').rename(self.root / 'old')
            (self.root / 'nested').symlink_to(self.root / 'old', target_is_directory=True)
            with self.assertRaises(OSError):
                with scan.source('nested/a.jpg'):
                    self.fail('followed symbolic link')

    def test_read_failure_is_relative_and_incomplete(self):
        self.file('a.jpg'); self.file('b.jpg')
        with patch.object(Scan, 'digest', side_effect=PermissionError('private absolute path')):
            code, result = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(result['groups'], [])
        self.assertEqual(result['errors'], [{'path': name, 'code': 'read_failed'} for name in ['a.jpg', 'b.jpg']])

    @unittest.skipIf(os.geteuid() == 0, 'root bypasses POSIX mode restrictions')
    def test_real_permission_failure(self):
        folder = self.root / 'locked'
        folder.mkdir()
        folder.chmod(0)
        try:
            code, report = self.report()
            self.assertEqual(code, 1)
            self.assertIn({'path': 'locked', 'code': 'directory_unreadable_or_changed'}, report['errors'])
        finally:
            folder.chmod(0o700)


class AdversarialIntegration(unittest.TestCase):
    setUp = ScanIntegration.setUp
    file = ScanIntegration.file
    report = ScanIntegration.report
    def test_change_during_read_is_detected(self):
        self.file('a.jpg'); self.file('b.jpg')
        with Scan(self.root) as scan:
            scan.enumerate()
            with self.assertRaises(OSError) as caught:
                with scan.source('a.jpg') as stream:
                    stream.read(1)
                    (self.root / 'a.jpg').write_bytes(b'changed')
            scan.invalidate('a.jpg', caught.exception)
            self.assertEqual(scan.db.execute('SELECT code FROM errors').fetchone()[0], 'file_changed')

    def test_late_directory_addition_is_incomplete(self):
        self.file('a.jpg'); self.file('b.jpg')
        original = Scan.digest
        def add(scan, path):
            result = original(scan, path)
            self.file('late.jpg', b'new')
            return result
        with patch.object(Scan, 'digest', add):
            code, result = self.report()
        self.assertEqual(code, 1)
        self.assertIn({'path': '.', 'code': 'directory_unreadable_or_changed'}, result['errors'])

    def test_file_replaced_by_symlink_does_not_get_read(self):
        self.file('a.jpg'); self.file('b.jpg')
        with Scan(self.root) as scan:
            scan.enumerate()
            (self.root / 'a.jpg').unlink()
            (self.root / 'a.jpg').symlink_to(self.root / 'b.jpg')
            with self.assertRaises(OSError):
                scan.digest('a.jpg')

    def test_root_ancestor_symlink_rejected(self):
        (self.root / 'actual').mkdir()
        (self.root / 'alias').symlink_to(self.root / 'actual', target_is_directory=True)
        (self.root / 'actual' / 'nested').mkdir()
        with self.assertRaises(OSError):
            with Scan(self.root / 'alias' / 'nested'):
                self.fail('accepted symlink ancestor')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux byte filenames fixture')
    def test_non_utf8_filename_reports_incomplete(self):
        raw_path = os.fsencode(self.root) + b'/bad\xff.jpg'
        fd = os.open(raw_path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        code, result = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(result['errors'][0]['code'], 'unsupported_filename_encoding')

    def test_comparison_read_failure_attributed_to_left(self):
        from contextlib import contextmanager
        self.file('a.jpg'); self.file('b.jpg')
        original = Scan._source
        class FailingRead:
            def read(self, size):
                raise PermissionError('synthetic read failure')
        @contextmanager
        def faulty(scan, path):
            with original(scan, path) as stream:
                yield FailingRead() if path == 'a.jpg' else stream
        with Scan(self.root) as scan:
            scan.enumerate()
            with patch.object(Scan, '_source', faulty):
                self.assertFalse(scan.equal('a.jpg', 'b.jpg'))
            self.assertEqual(scan.db.execute('SELECT path,code FROM errors').fetchall(), [('a.jpg', 'read_failed')])

    def test_parent_traversal_root_rejected(self):
        with self.assertRaises(ValueError):
            with Scan(str(self.root) + '/../' + self.root.name):
                self.fail('accepted parent traversal')


if __name__ == '__main__':
    unittest.main()
