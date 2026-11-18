import os
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

from dup_media.move_fs import Location, MoveError
from dup_media.move_darwin import physical
from dup_media.relocate import Relocation
from tests.macos_fixtures import MacFixture, set_attribute, get_attribute
from tests.move_fixtures import tree
from tests.integration import test_relocate as portable


class MacRelocation(MacFixture):
    def test_real_cross_device_integration(self):
        cross = os.environ.get('MOVE_CROSS_ROOT')
        if not cross:
            if os.environ.get('REQUIRE_MAC_MOVE_TESTS') == '1':
                self.fail('second APFS filesystem is mandatory')
            self.skipTest('provide second APFS filesystem')
        self.assertNotEqual(Path(cross).stat().st_dev, self.source.stat().st_dev)
        with tempfile.TemporaryDirectory(dir=cross) as t:
            self.dest = Path(t).resolve() / 'dest'
            code, records = self.run_move()
            self.assertEqual(code, 0, records)
            self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
            self.assertFalse((self.source / 'nested/b.jpg').exists())

    def test_real_subordinate_mount_is_rejected(self):
        cross = os.environ.get('MOVE_CROSS_ROOT')
        if not cross:
            if os.environ.get('REQUIRE_MAC_MOVE_TESTS') == '1':
                self.fail('second APFS filesystem is mandatory')
            self.skipTest('provide second APFS filesystem')
        from dup_media.move_darwin import mounts
        self.assertNotEqual(Path(cross).stat().st_dev, Path(cross).parent.stat().st_dev)
        with self.assertRaises(MoveError) as caught:
            mounts([Location(Path(cross).resolve().parent)])
        self.assertEqual(caught.exception.code, 'nested_mount_unsupported')

    def test_metadata_loss_policy_and_journal(self):
        victim = self.source / 'nested/b.jpg'
        victim.chmod(0o644)
        os.utime(victim, ns=(1234567890000000000, 1234567890000000000))
        set_attribute(victim, 'com.apple.metadata:fixture', b'original synthetic value')
        code, records = self.run_move()
        self.assertEqual(code, 0, records)
        self.assertEqual(records[0]['metadata_policy'], 'macos-data-only')
        target = self.dest / 'nested/b.jpg'
        self.assertEqual(target.read_bytes(), b'a' * 100)
        self.assertIsNone(get_attribute(target, 'com.apple.metadata:fixture'))
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertNotEqual(target.stat().st_mtime_ns, 1234567890000000000)
        self.assertEqual((self.source / 'a.jpg').read_bytes(), b'a' * 100)
        self.assertFalse(victim.exists())
        with sqlite3.connect(self.journal / 'journal.sqlite') as db:
            self.assertEqual(db.execute('SELECT state,metadata FROM items').fetchone(),
                             ('source_removed', '{"policy": "macos-data-only"}'))

    def test_resource_fork_on_keeper_or_victim_blocks_whole_plan(self):
        for name in ['a.jpg', 'nested/b.jpg']:
            for dry in [True, False]:
                with self.subTest(name=name, dry=dry), tempfile.TemporaryDirectory() as t:
                    from tests.move_fixtures import make_tree
                    from dup_media.scan import DEFAULT_EXTENSIONS
                    import io
                    root = Path(t).resolve()
                    make_tree(root / 'source')
                    set_attribute(root / 'source' / name, 'com.apple.ResourceFork', b'fork data')
                    before = tree(root / 'source')
                    out = io.StringIO()
                    code = Relocation(root / 'source', root / 'dest', None if dry else root / 'journal').run(DEFAULT_EXTENSIONS, out, dry)
                    self.assertEqual(code, 1, out.getvalue())
                    self.assertIn('resource_fork_unsupported', out.getvalue())
                    self.assertEqual(tree(root / 'source'), before)
                    self.assertFalse((root / 'dest').exists())
                    self.assertFalse((root / 'journal').exists())

    def test_late_resource_fork_on_keeper_or_victim_retains_source(self):
        for name in ['a.jpg', 'nested/b.jpg']:
            with self.subTest(name=name):
                def inject(stage, path):
                    if stage == 'before_unlink':
                        set_attribute(self.source / name, 'com.apple.ResourceFork', b'late fork')
                with patch('dup_media.relocate.checkpoint', inject):
                    code, records = self.run_move()
                self.assertEqual(code, 1, records)
                self.assertTrue((self.source / 'nested/b.jpg').exists())
                self.assertEqual(records[-1]['moved'], 0)
                # Separate fixture for the second participant.
                if name == 'a.jpg':
                    self.temp.cleanup()
                    self.setUp()

    def test_physical_firmlink_overlap_and_scratch_are_rejected(self):
        physical_source = Path(physical(Location(self.source)))
        if physical_source == self.source:
            self.skipTest('fixture has no alternate firmlink spelling')
        with self.assertRaises((ValueError, OSError)):
            Relocation(self.source, physical_source / 'child').run(frozenset({'jpg'}), __import__('io').StringIO(), True)
        with patch.dict(os.environ, {'TMPDIR': str(physical_source)}):
            with self.assertRaises((ValueError, OSError)):
                self.run_move(dry=True)
        self.assertFalse(self.dest.exists())

    def test_fullsync_failure_retains_source(self):
        def fail(fd):
            raise OSError('synthetic fullsync failure')
        with patch('dup_media.relocate.sync_file', fail):
            code, records = self.run_move()
        self.assertEqual(code, 1, records)
        self.assertTrue((self.source / 'nested/b.jpg').exists())
        self.assertFalse((self.dest / 'nested/b.jpg').exists())

    def test_late_destination_resource_fork_retains_source(self):
        def inject(stage, path):
            if stage == 'before_unlink':
                set_attribute(self.dest / path, 'com.apple.ResourceFork', b'late target fork')
        with patch('dup_media.relocate.checkpoint', inject):
            code, records = self.run_move()
        self.assertEqual(code, 1, records)
        self.assertTrue((self.source / 'nested/b.jpg').exists())

    def test_flagged_file_is_rejected(self):
        import stat
        victim = self.source / 'nested/b.jpg'
        os.chflags(victim, stat.UF_NODUMP)
        try:
            code, records = self.run_move()
            self.assertEqual(code, 1, records)
            self.assertIn('unsupported_inode_flags', str(records))
            self.assertFalse(self.dest.exists())
            self.assertFalse(self.journal.exists())
        finally:
            os.chflags(victim, 0)

    def test_post_publication_fullsync_failure_retains_source_and_copy(self):
        from dup_media.move_darwin import sync_file
        calls = 0
        def fail_second(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('synthetic publication flush failure')
            sync_file(fd)
        with patch('dup_media.relocate.sync_file', fail_second):
            code, records = self.run_move()
        self.assertEqual(code, 1, records)
        self.assertEqual(calls, 2)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertEqual(records[-1]['moved'], 0)
        with sqlite3.connect(self.journal / 'journal.sqlite') as db:
            self.assertEqual(db.execute('SELECT state FROM items').fetchone()[0], 'staged_verified')

    def test_journal_parent_replacement_stops_before_removal(self):
        def inject(stage, path):
            if stage == 'published':
                self.journal.rename(self.base / 'saved-journal')
                self.journal.mkdir()
        with patch('dup_media.relocate.checkpoint', inject):
            code, records = self.run_move()
        self.assertEqual(code, 1, records)
        self.assertTrue((self.source / 'nested/b.jpg').exists())
        self.assertEqual(list(self.journal.iterdir()), [])


# Run existing byte/path/failure contracts on APFS without activating Linux metadata tests.
for name in [
    'test_dry_run_and_empty_plan_do_not_create_roots_or_journal',
    'test_hardlinked_three_member_group_keeps_first_path',
    'test_zero_bytes_and_unicode_group',
    'test_preexisting_identical_file_directory_and_link_never_overwritten',
    'test_late_destination_conflict_preserves_both_originals',
    'test_metadata_failure_and_early_journal_failure_never_unlink_source',
    'test_unlink_failure_keeps_verified_destination_and_source',
    'test_keeper_change_stops_before_removal',
    'test_detected_change_and_hash_collision_do_not_create_false_group',
    'test_destination_symlink_parent_is_rejected',
    'test_source_symlink_replacement_does_not_remove_replacement',
    'test_unsupported_no_replace_link_retains_source',
    'test_destination_parent_replaced_after_publish_blocks_source_removal',
    'test_advisory_lock_blocks_second_writer',
    'test_late_in_place_source_or_destination_changes_are_detected',
    'test_existing_empty_destination_and_nested_parents_succeed',
    'test_unlink_to_journal_commit_gap_is_recoverable',
    'test_partial_batch_stops_after_second_victim_error',
    'test_copy_io_failure_retains_source_and_records_error',
    'test_sqlite_spill_directory_is_pinned_outside_both_trees',
]:
    setattr(MacRelocation, name, getattr(portable.TransferIntegration, name))
