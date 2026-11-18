"""Original disposable bytes and native writer records; no personal archives."""
from contextlib import closing
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from unittest.mock import patch

from dup_media.recovery import CONTROL
from dup_media.relocate import Relocation
from dup_media.revert import Revert
from dup_media.scan import DEFAULT_EXTENSIONS
from tests.move_fixtures import namespace_snapshot

REPO = Path(__file__).resolve().parents[1]


class RevertCases:
    """Same contract exercised through native integration and shipped CLI wrappers."""
    cli_mode = False

    def forward(self):
        if self.cli_mode:
            p = subprocess.run([sys.executable, '-m', 'dup_media', '--move-duplicates',
                                str(self.source), '--destination', str(self.dest),
                                '--journal', str(self.journal), '--exclusive-access'],
                               cwd=REPO, capture_output=True, text=True, timeout=30)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        else:
            code, rows = self.run_move()
            self.assertEqual(code, 0, rows)

    def revert(self, dry=False, legacy=False, operation=None):
        if self.cli_mode:
            args = [sys.executable, '-m', 'dup_media', '--revert-move', str(self.dest)]
            args += ['--dry-run'] if dry else ['--exclusive-access']
            if legacy:
                args += ['--original-root', str(self.source), '--move-journal', str(self.journal)]
            if operation:
                args += ['--operation', operation]
            p = subprocess.run(args, cwd=REPO, capture_output=True, text=True, timeout=30)
            self.assertNotIn(str(self.base), p.stdout + p.stderr)
            return p.returncode, [json.loads(line) for line in p.stdout.splitlines()]
        out = io.StringIO()
        code = Revert(self.dest, self.source if legacy else None,
                      self.journal if legacy else None, operation).run(out, dry)
        return code, [json.loads(s) for s in out.getvalue().splitlines()]

    def manifest(self):
        return next((self.dest / CONTROL / 'operations').glob('*/manifest.sqlite'))

    def edit(self, sql, args=(), journal=False):
        with closing(sqlite3.connect(self.journal / 'journal.sqlite' if journal else self.manifest())) as db:
            db.execute(sql, args); db.commit()

    def legacy(self):
        # The external writer/schema is unchanged from4af6c1f. Remove only the new
        # sidecar from a synthetic operation to model that historical on-disk input.
        shutil.rmtree(self.dest / CONTROL)
        with closing(sqlite3.connect(self.journal / 'journal.sqlite')) as db:
            self.assertEqual([x[1] for x in db.execute('PRAGMA table_info(roots)')], ['kind', 'dev', 'ino'])

    def blocked(self, error, legacy=False):
        before = namespace_snapshot(self.base)
        for dry in [True, False]:
            code, rows = self.revert(dry, legacy)
            self.assertEqual(code, 1, rows)
            self.assertIn(error, [r.get('code') for r in rows])
            self.assertEqual(rows[-1]['restored'], 0)
            self.assertFalse(rows[-1]['complete'])
            self.assertEqual(namespace_snapshot(self.base), before)

    def test_round_trip_preview_extra_original_dirs_and_repeat(self):
        before = (self.source / 'nested/b.jpg').read_bytes()
        self.forward()
        # Revert must not need a duplicate keeper or extension-based regrouping.
        (self.source / 'a.jpg').unlink()
        (self.source / 'extra/keeper-folder').mkdir(parents=True)
        (self.dest / 'unregistered.txt').write_bytes(b'leave this alone')
        snapshot = namespace_snapshot(self.base)
        code, rows = self.revert(True)
        self.assertEqual(code, 0, rows)
        self.assertEqual(rows[-1]['planned'], 1)
        self.assertEqual(namespace_snapshot(self.base), snapshot)
        code, rows = self.revert()
        self.assertEqual(code, 0, rows)
        self.assertEqual(rows[-1]['restored'], 1)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), before)
        self.assertFalse((self.dest / 'nested/b.jpg').exists())
        self.assertEqual((self.dest / 'unregistered.txt').read_bytes(), b'leave this alone')
        snapshot = namespace_snapshot(self.base)
        code, rows = self.revert()
        self.assertEqual(code, 0, rows)
        self.assertEqual(rows[-1]['reason'], 'already_reverted')
        self.assertEqual(namespace_snapshot(self.base), snapshot)

    def test_missing_original_directory_and_extra_archive_directory_block(self):
        self.forward()
        (self.source / 'nested').rmdir()
        self.blocked('structure_mismatch')
        (self.source / 'nested').mkdir()
        (self.dest / 'empty-new-subfolder').mkdir()
        self.blocked('structure_mismatch')
        (self.source / 'empty-new-subfolder').mkdir()
        code, rows = self.revert()
        self.assertEqual(code, 0, rows)

    def test_existing_identical_different_directory_or_symlink_never_overwritten(self):
        self.forward()
        target = self.source / 'nested/b.jpg'
        for kind in ['identical', 'different', 'directory', 'symlink']:
            with self.subTest(kind=kind):
                if kind == 'directory': target.mkdir()
                elif kind == 'symlink': target.symlink_to('../unique.wav')
                else: target.write_bytes(b'a' * 100 if kind == 'identical' else b'other')
                self.blocked('restore_target_exists')
                if kind == 'directory': target.rmdir()
                else: target.unlink()

    def test_same_size_archive_mutation_and_root_replacement_refuse(self):
        self.forward()
        p = self.dest / 'nested/b.jpg'; p.write_bytes(b'z' * 100)
        self.blocked('archive_changed')
        original = self.source
        original.rename(self.base / 'saved-original')
        original.mkdir(); (original / 'nested').mkdir()
        self.blocked('root_identity_mismatch')

    def test_later_conflict_blocks_every_file_before_receipt_creation(self):
        (self.source / 'c.jpg').write_bytes(b'second exact group')
        (self.source / 'zz').mkdir()
        (self.source / 'zz/d.jpg').write_bytes(b'second exact group')
        self.forward()
        (self.source / 'zz/d.jpg').write_bytes(b'existing unrelated file')
        self.blocked('restore_target_exists')
        self.assertTrue((self.dest / 'nested/b.jpg').exists())
        self.assertFalse((self.manifest().parent / 'revert').exists())

    def test_native_parent_permissions_block_without_mutation(self):
        self.forward()
        if sys.platform == 'darwin':
            parent = self.dest / 'nested'
            original = parent.stat().st_mode
            try:
                parent.chmod(0o555)
                self.blocked('source_permission_denied')
            finally:
                parent.chmod(original)
            parent = self.source / 'nested'
            original = parent.stat().st_mode
            try:
                parent.chmod(0o555)
                self.blocked('destination_permission_denied')
            finally:
                parent.chmod(original)
        else:
            import array
            import fcntl
            for parent, bit, error in [(self.dest / 'nested', 0x20, 'source_directory_flags_unsupported'),
                                       (self.source / 'nested', 0x40, 'destination_directory_flags_unsupported')]:
                fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
                flags = array.array('I', [0]); fcntl.ioctl(fd, 0x80086601, flags, True)
                original = flags[0]
                try:
                    flags[0] |= bit; fcntl.ioctl(fd, 0x40086602, flags, True)
                    self.blocked(error)
                finally:
                    flags[0] = original; fcntl.ioctl(fd, 0x40086602, flags, True); os.close(fd)

    def test_metadata_policy_and_control_permissions(self):
        victim = self.source / 'nested/b.jpg'
        victim.chmod(0o640); os.utime(victim, ns=(1234567890123456789, 1234567890123456789))
        if sys.platform == 'darwin':
            from tests.macos_fixtures import set_attribute
            set_attribute(victim, 'user.synthetic', b'original disposable metadata')
        else:
            os.setxattr(victim, 'user.synthetic', b'original disposable metadata')
        self.forward()
        self.assertEqual(self.manifest().stat().st_mode & 0o777, 0o600)
        code, rows = self.revert()
        self.assertEqual(code, 0, rows)
        if sys.platform == 'darwin':
            from tests.macos_fixtures import get_attribute
            self.assertEqual(rows[0]['metadata_policy'], 'macos-data-only')
            self.assertEqual(victim.stat().st_mode & 0o777, 0o600)
            self.assertIsNone(get_attribute(victim, 'user.synthetic'))
        else:
            self.assertEqual(victim.stat().st_mode & 0o777, 0o640)
            self.assertEqual(victim.stat().st_mtime_ns, 1234567890123456789)
            self.assertEqual(os.getxattr(victim, 'user.synthetic'), b'original disposable metadata')

    def test_legacy_completed_round_trip_preserves_original_journal_bytes(self):
        self.forward(); self.legacy()
        before = (self.journal / 'journal.sqlite').read_bytes()
        code, rows = self.revert(True, True)
        self.assertEqual(code, 0, rows)
        code, rows = self.revert(False, True)
        self.assertEqual(code, 0, rows)
        self.assertEqual(rows[0]['provenance'], 'legacy-journal')
        self.assertEqual((self.journal / 'journal.sqlite').read_bytes(), before)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)
        code, rows = self.revert(False, True)
        self.assertEqual(code, 0, rows)
        self.assertEqual(rows[-1]['reason'], 'already_reverted')

    def test_legacy_intermediate_receipt_and_lingering_stage_refuse(self):
        self.forward(); self.legacy()
        self.edit("UPDATE items SET state='destination_verified'", journal=True)
        self.blocked('operation_incomplete', True)
        self.edit("UPDATE items SET state='source_removed'", journal=True)
        with closing(sqlite3.connect(self.journal / 'journal.sqlite')) as db:
            stage = db.execute('SELECT stage FROM items').fetchone()[0]
        (self.dest / 'nested' / stage).write_bytes(b'retained original staging control')
        self.blocked('operation_incomplete', True)

    def test_pending_manifest_or_incomplete_revert_refuse(self):
        self.forward()
        self.edit('UPDATE operation SET value=? WHERE key=?', ('"PENDING"', 'state'))
        self.blocked('operation_incomplete')
        self.edit('UPDATE operation SET value=? WHERE key=?', ('"COMPLETE"', 'state'))
        pending = self.manifest().parent / 'revert'; pending.mkdir(mode=0o700)
        self.blocked('io_failure')

    def test_malformed_schema_paths_and_version_refuse_without_mutation(self):
        self.forward()
        for sql, args, error in [
            ('UPDATE operation SET value=? WHERE key=?', ('2', 'version'), 'recovery_unsupported_version'),
            ('UPDATE operation SET value=? WHERE key=?', ('1', 'version'), None),
            ('UPDATE items SET path=?', ('../outside.jpg',), 'recovery_invalid'),
            ('UPDATE items SET path=?', ('nested/b.jpg',), None),
            ('CREATE VIEW unexpected AS SELECT * FROM items', (), 'recovery_invalid')]:
            self.edit(sql, args)
            if error: self.blocked(error)

    def test_operation_ambiguity_requires_explicit_id(self):
        self.forward()
        first = self.manifest().parent.name
        for name in ['c.mp4', 'd.mp4']:
            (self.source / name).write_bytes(b'second group')
        self.journal = self.base / 'second-operation'
        self.forward()
        self.blocked('recovery_ambiguous')
        code, rows = self.revert(operation=first)
        self.assertEqual(code, 0, rows)
        self.assertTrue((self.source / 'nested/b.jpg').exists())
        self.assertTrue((self.dest / 'd.mp4').exists())

    def test_zero_unicode_hardlink_paths_round_trip(self):
        os.link(self.source / 'a.jpg', self.source / 'c.jpg')
        (self.source / '0.JPG').touch(); (self.source / '雪.mp4').touch()
        self.forward()
        code, rows = self.revert()
        self.assertEqual(code, 0, rows)
        self.assertEqual(rows[-1]['restored'], 3)
        self.assertEqual((self.source / 'c.jpg').read_bytes(), b'a' * 100)
        self.assertEqual((self.source / '雪.mp4').read_bytes(), b'')

    def test_real_second_volume_round_trip(self):
        target = os.environ.get('MOVE_CROSS_ROOT')
        if not target:
            if os.environ.get('REQUIRE_MOVE_TESTS') == '1' or os.environ.get('REQUIRE_MAC_MOVE_TESTS') == '1':
                self.fail('mandatory second volume missing')
            self.skipTest('provide second native filesystem')
        with tempfile.TemporaryDirectory(dir=target) as t:
            self.dest = Path(t) / 'archive'
            self.assertNotEqual(self.source.stat().st_dev, Path(t).stat().st_dev)
            self.forward()
            code, rows = self.revert()
            self.assertEqual(code, 0, rows)
            self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)
            self.assertFalse((self.dest / 'nested/b.jpg').exists())


class RevertFaultCases:
    def test_forward_manifest_finalization_failure_is_not_revertible(self):
        with patch('dup_media.relocate.Manifest.complete', side_effect=OSError('synthetic completion failure')):
            code, rows = self.run_move()
        self.assertEqual(code, 1, rows)
        self.assertFalse((self.source / 'nested/b.jpg').exists())
        self.blocked('operation_incomplete')

    def test_archive_replacement_before_unlink_is_retained(self):
        self.forward()
        def replace(stage, path):
            if stage == 'before_unlink':
                (self.dest / path).unlink()
                (self.dest / path).write_bytes(b'other writer')
        with patch('dup_media.revert.checkpoint', replace):
            code, rows = self.revert()
        self.assertEqual(code, 1, rows)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'other writer')
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)

    def test_post_publication_sync_failure_retains_archive_and_restoration(self):
        self.forward()
        from dup_media.revert import sync_file
        calls = 0
        def flush(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('synthetic publication flush failure')
            sync_file(fd)
        with patch('dup_media.revert.sync_file', flush):
            code, rows = self.revert()
        self.assertEqual(code, 1, rows)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)

    def test_copy_failure_preserves_archive_and_blocks_retry(self):
        self.forward()
        with patch('dup_media.revert.copy_stream', side_effect=OSError('synthetic copy failure')):
            code, rows = self.revert()
        self.assertEqual(code, 1, rows)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertFalse((self.source / 'nested/b.jpg').exists())
        self.blocked('revert_incomplete')

    def test_late_destination_conflict_retains_archive_and_replacement(self):
        self.forward()
        def change(stage, path):
            if stage == 'staged_verified':
                (self.source / path).write_bytes(b'unrelated replacement')
        with patch('dup_media.revert.checkpoint', change):
            code, rows = self.revert()
        self.assertEqual(code, 1, rows)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'unrelated replacement')
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)

    def test_unlink_receipt_gap_never_auto_resumes(self):
        self.forward()
        def gap(stage, path):
            if stage == 'after_unlink':
                raise OSError('synthetic receipt gap')
        with patch('dup_media.revert.checkpoint', gap):
            code, rows = self.revert()
        self.assertEqual(code, 1, rows)
        self.assertEqual(rows[-1]['restored'], 0)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertFalse((self.dest / 'nested/b.jpg').exists())
        self.blocked('revert_incomplete')


class RevertSignalCases:
    def test_cli_signals_at_durable_boundaries_refuse_retry(self):
        self.forward()
        for boundary, sig, expected in [('staged_verified', 'SIGINT', 130),
                                         ('published', 'SIGKILL', -9),
                                         ('after_unlink', 'SIGKILL', -9),
                                         ('archive_removed', 'SIGKILL', -9)]:
            with self.subTest(boundary=boundary):
                # Root binding must remain genuine: create fresh disposable moves,
                # rather than copy a manifest onto another root identity.
                if boundary != 'staged_verified':
                    shutil.rmtree(self.dest)
                    self.journal = self.base / (boundary + '-forward')
                    if (self.source / 'nested/b.jpg').exists():
                        (self.source / 'nested/b.jpg').unlink()
                    (self.source / 'nested/b.jpg').write_bytes(b'a' * 100)
                    self.forward()
                driver = '''
import os,signal,sys
from unittest.mock import patch
from dup_media.__main__ import main
boundary,sig=sys.argv[1:3]; del sys.argv[1:3]
def observe(stage,path):
    if stage==boundary: os.kill(os.getpid(),getattr(signal,sig))
with patch('dup_media.revert.checkpoint',observe): sys.exit(main())
'''
                p = subprocess.run([sys.executable, '-c', driver, boundary, sig,
                                    '--revert-move', str(self.dest), '--exclusive-access'],
                                   cwd=REPO, capture_output=True, text=True, timeout=30)
                self.assertEqual(p.returncode, expected, p.stdout+p.stderr)
                if boundary in ('after_unlink', 'archive_removed'):
                    self.assertFalse((self.dest / 'nested/b.jpg').exists())
                    self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a'*100)
                else:
                    self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a'*100)
                code, rows = self.revert()
                self.assertEqual(code, 1, rows)
                self.assertIn('revert_incomplete', [r.get('code') for r in rows])
