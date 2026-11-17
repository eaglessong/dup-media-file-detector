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
