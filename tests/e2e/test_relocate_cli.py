import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from tests.move_fixtures import MoveFixture, tree

REPO = Path(__file__).resolve().parents[2]


class MoveCliModes(unittest.TestCase):
    def test_invalid_modes_and_nested_destination_fail_before_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            for flags in [['--dry-run'], ['--move-duplicates'],
                          ['--move-duplicates', '--destination', str(root / 'child'), '--dry-run']]:
                p = subprocess.run([sys.executable, '-m', 'dup_media', str(root), *flags], cwd=REPO, capture_output=True, text=True)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertFalse((root / 'child').exists())
                self.assertNotIn(str(root), p.stderr)


class MoveCli(MoveFixture):
    def cli(self, dry=False, extra=()):
        args = [sys.executable, '-m', 'dup_media', '--move-duplicates', str(self.source), '--destination', str(self.dest)]
        args += ['--dry-run'] if dry else ['--journal', str(self.journal), '--exclusive-access']
        return subprocess.run([*args, *extra], cwd=REPO, capture_output=True, text=True, timeout=30)

    def test_shipped_cli_dry_run_then_execution_and_repeat(self):
        before = tree(self.source)
        p = self.cli(dry=True)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        rows = [json.loads(s) for s in p.stdout.splitlines()]
        self.assertEqual(rows[1]['keeper'], 'a.jpg')
        self.assertEqual(rows[-1]['planned'], 1)
        self.assertEqual(tree(self.source), before)
        self.assertFalse(self.dest.exists())
        p = self.cli()
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertEqual(json.loads(p.stdout.splitlines()[-1])['moved'], 1)
        self.assertNotIn(str(self.source), p.stdout + p.stderr)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertFalse((self.source / 'nested/b.jpg').exists())
        self.assertEqual((self.source / 'a.jpg').read_bytes(), b'a' * 100)
        # Reusing a journal never overwrites it.
        self.assertEqual(self.cli().returncode, 2)

    def test_real_cross_device_cli_move(self):
        target = Path('/dev/shm')
        self.assertTrue(target.is_dir(), 'CI must provide a second filesystem')
        self.assertNotEqual(target.stat().st_dev, self.source.stat().st_dev)
        with tempfile.TemporaryDirectory(dir=target) as t:
            self.dest = Path(t) / 'dest'
            p = self.cli()
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
            self.assertFalse((self.source / 'nested/b.jpg').exists())
            self.assertEqual((self.source / 'a.jpg').read_bytes(), b'a' * 100)

    def test_destination_collision_and_extension_override(self):
        self.dest.mkdir()
        (self.dest / 'nested').mkdir()
        target = self.dest / 'nested/b.jpg'
        target.write_bytes(b'existing')
        before = tree(self.source)
        p = self.cli()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual(tree(self.source), before)
        self.assertEqual(target.read_bytes(), b'existing')
        self.assertFalse(self.journal.exists())
        p = self.cli(extra=['--extensions', 'wav'])
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertEqual(json.loads(p.stdout.splitlines()[-1])['planned'], 0)
