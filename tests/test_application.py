"""Application contract checks, separate from framework validation."""
import argparse
import unittest
from dup_media.__main__ import extensions
from dup_media.scan import DEFAULT_EXTENSIONS


class ApplicationChecks(unittest.TestCase):
    def test_extension_contract(self):
        self.assertEqual(extensions('JPG,png'), {'jpg', 'png'})
        self.assertTrue({'jpg', 'mp4', 'mp3', 'heic'} <= DEFAULT_EXTENSIONS)
        for invalid in ['', '.jpg', 'jpg,', '../jpg']:
            with self.assertRaises(argparse.ArgumentTypeError):
                extensions(invalid)


class SummaryArithmeticChecks(unittest.TestCase):
    def test_indexed_totals_beyond_sqlite_sum_range(self):
        # Synthetic SQLite rows exercise arithmetic/serialization only, not a huge tree.
        import io
        import json
        from pathlib import Path
        import tempfile
        from dup_media.scan import Scan
        with tempfile.TemporaryDirectory() as folder:
            with Scan(Path(folder).resolve()) as scan:
                for name in ['a.jpg', 'b.jpg']:
                    scan.db.execute('INSERT INTO files(path,size) VALUES (?,?)', (name, 2**62))
                scan.db.execute('INSERT INTO files(path,size,valid) VALUES (?,?,0)', ('invalid.jpg', 10))
                output = io.StringIO()
                self.assertEqual(scan.write(output), 0)
                self.assertEqual(json.loads(output.getvalue())['summary'],
                                 {'media_file_count': 2, 'total_size_bytes': 2**63, 'complete': True})


class RevertArguments(unittest.TestCase):
    def test_explicit_mode_and_legacy_pair_required(self):
        import subprocess
        import sys
        for extra in [[], ['--move-duplicates'], ['--original-root', 'original'],
                      ['--exclusive-access', '--extensions', 'jpg'],
                      ['--exclusive-access', '--destination', 'other'],
                      ['--exclusive-access', '--journal', 'new-operation']]:
            with self.subTest(extra=extra):
                result = subprocess.run([sys.executable, '-m', 'dup_media', '--revert-move',
                                         'nonexistent-disposable-placeholder', *extra],
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertIn('revert requires', result.stderr)
