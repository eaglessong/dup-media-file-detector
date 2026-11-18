import errno
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
from unittest.mock import patch
import unittest

from dup_media.move_fs import Location, MoveError, metadata
from dup_media.relocate import Relocation
from dup_media.scan import Scan
from tests.move_fixtures import MoveFixture, tree


class RootSafety(unittest.TestCase):
    def test_overlap_missing_child_and_symlink_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            source = root / 'source'
            source.mkdir()
            for dest in [source, source / 'missing/child', root]:
                with self.assertRaises((ValueError, OSError)):
                    Relocation(source, dest)
                self.assertEqual(list(source.iterdir()), [])
            (root / 'alias').symlink_to(source, target_is_directory=True)
            with self.assertRaises(OSError):
                Relocation(source, root / 'alias' / 'dest')
            # Prefix lookalike is not a descendant.
            Relocation(source, root / 'source-backup')

    def test_destination_containing_scratch_is_rejected_before_scan(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            source = root / 'source'
            source.mkdir()
            destination = root / 'dest'
            destination.mkdir()
            with patch.dict(os.environ, {'TMPDIR': str(destination)}):
                with self.assertRaises(ValueError):
                    Relocation(source, destination)
            self.assertEqual(list(destination.iterdir()), [])


class TransferIntegration(MoveFixture):
    def test_exact_move_preserves_bytes_metadata_and_unique_files(self):
        before = tree(self.source)
        victim = self.source / 'nested/b.jpg'
        victim.chmod(0o640)
        os.utime(victim, ns=(1234567890123456789, 1234567890123456789))
        os.setxattr(victim, 'user.original', b'fixture')
        expected = tree(self.source)['nested/b.jpg']
        code, records = self.run_move()
        self.assertEqual(code, 0, records)
        self.assertEqual(set(tree(self.source)), {'a.jpg', 'unique.wav', 'ignored.txt'})
        self.assertEqual(tree(self.source)['a.jpg'], before['a.jpg'])
        self.assertEqual(tree(self.dest), {'nested/b.jpg': expected})
        self.assertEqual(os.getxattr(self.dest / 'nested/b.jpg', 'user.original'), b'fixture')
        self.assertEqual(records[-1]['moved'], 1)
        with sqlite3.connect(self.journal / 'journal.sqlite') as db:
            self.assertEqual(db.execute('SELECT path,state FROM items').fetchall(), [('nested/b.jpg', 'source_removed')])

    def test_dry_run_and_empty_plan_do_not_create_roots_or_journal(self):
        before = tree(self.source)
        code, records = self.run_move(dry=True)
        self.assertEqual(code, 0, records)
        self.assertEqual(records[1]['source'], 'nested/b.jpg')
        self.assertEqual(records[1]['keeper'], 'a.jpg')
        self.assertEqual(records[-1]['moved'], 0)
        self.assertEqual(tree(self.source), before)
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.journal.exists())
        (self.source / 'nested/b.jpg').unlink()
        code, records = self.run_move()
        self.assertEqual(code, 0, records)
        self.assertEqual(records[-1]['planned'], 0)
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.journal.exists())

    def test_hardlinked_three_member_group_keeps_first_path(self):
        os.link(self.source / 'a.jpg', self.source / 'c.jpg')
        os.link(self.source / 'a.jpg', self.source / 'd.jpg')
        code, records = self.run_move()
        self.assertEqual(code, 0, records)
        self.assertEqual(records[-1]['moved'], 3)
        self.assertEqual(set(tree(self.source)), {'a.jpg', 'unique.wav', 'ignored.txt'})
        self.assertEqual(set(tree(self.dest)), {'c.jpg', 'd.jpg', 'nested/b.jpg'})
        self.assertTrue(all(v[0] == b'a' * 100 for v in tree(self.dest).values()))

    def test_zero_bytes_and_unicode_group(self):
        for name in ['0.JPG', '雪.mp4']:
            (self.source / name).touch()
        code, records = self.run_move()
        self.assertEqual(code, 0, records)
        self.assertTrue((self.source / '0.JPG').exists())
        self.assertFalse((self.source / '雪.mp4').exists())
        self.assertEqual((self.dest / '雪.mp4').read_bytes(), b'')

    def test_preexisting_identical_file_directory_and_link_never_overwritten(self):
        (self.dest / 'nested').mkdir(parents=True)
        p = self.dest / 'nested/b.jpg'
        before = tree(self.source)
        for kind in ['file', 'directory', 'link']:
            if kind == 'file': p.write_bytes(b'a' * 100)
            elif kind == 'directory': p.mkdir()
            else: p.symlink_to('absent')
            code, records = self.run_move()
            self.assertEqual(code, 1, records)
            self.assertEqual(records[-1]['moved'], 0)
            self.assertEqual(tree(self.source), before)
            self.assertFalse(self.journal.exists())
            if kind == 'directory': p.rmdir()
            else: p.unlink()

    def test_late_destination_conflict_preserves_both_originals(self):
        def collision(stage, path):
            if stage == 'staged_verified':
                (self.dest / path).write_bytes(b'other writer')
        with patch('dup_media.relocate.checkpoint', collision):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'other writer')
        self.assertEqual(records[-1]['moved'], 0)

    def test_metadata_failure_and_early_journal_failure_never_unlink_source(self):
        before = tree(self.source)
        with patch('dup_media.relocate.apply_metadata', side_effect=OSError(errno.ENOSPC, 'synthetic disk full')):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual(tree(self.source), before)
        self.assertFalse((self.dest / 'nested/b.jpg').exists())
        self.journal = self.base / 'second-operation'
        with patch('dup_media.move_journal.Journal.state', side_effect=sqlite3.OperationalError('synthetic journal full')) as fault:
            code, records = self.run_move()
            fault.assert_called()
        self.assertEqual(code, 1)
        self.assertEqual(tree(self.source), before)

    def test_unlink_failure_keeps_verified_destination_and_source(self):
        original = os.unlink
        def fail(path, *args, **kwargs):
            if path == 'b.jpg':
                raise PermissionError('synthetic unlink failure')
            return original(path, *args, **kwargs)
        with patch('dup_media.relocate.os.unlink', fail):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
        with sqlite3.connect(self.journal / 'journal.sqlite') as db:
            self.assertEqual(db.execute('SELECT state FROM items').fetchone()[0], 'destination_verified')

    def test_keeper_change_stops_before_removal(self):
        def mutate(stage, path):
            if stage == 'published':
                (self.source / 'a.jpg').write_bytes(b'x' * 100)
        with patch('dup_media.relocate.checkpoint', mutate):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)

    def test_trusted_attributes_are_not_silently_discarded(self):
        p = self.source / 'nested/b.jpg'
        os.setxattr(p, 'trusted.fixture', b'must not be hidden')
        code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertIn('unsupported_metadata', str(records))
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.journal.exists())

    def test_detected_change_and_hash_collision_do_not_create_false_group(self):
        original = Scan.enumerate
        def mutate(scan):
            original(scan)
            (self.source / 'unique.wav').write_bytes(b'changed')
        with patch.object(Scan, 'enumerate', mutate):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertFalse(self.dest.exists())
        (self.source / 'nested/b.jpg').write_bytes(b'b' * 100)
        with patch.object(Scan, 'digest', return_value='forced-collision'):
            code, records = self.run_move()
        self.assertEqual(code, 0, records)
        self.assertEqual(records[-1]['planned'], 0)

    def test_destination_symlink_parent_is_rejected(self):
        outside = self.base / 'outside'
        outside.mkdir()
        self.dest.mkdir()
        (self.dest / 'nested').symlink_to(outside, target_is_directory=True)
        code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertTrue((self.source / 'nested/b.jpg').exists())

    def test_source_symlink_replacement_does_not_remove_replacement(self):
        def replace(stage, path):
            if stage == 'before_unlink':
                victim = self.source / path
                victim.unlink()
                victim.symlink_to('../unique.wav')
        with patch('dup_media.relocate.checkpoint', replace):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertTrue((self.source / 'nested/b.jpg').is_symlink())
        self.assertEqual((self.source / 'unique.wav').read_bytes(), b'u' * 50)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)

    def test_real_acl_and_nodump_flags_block_without_mutation(self):
        import array
        import fcntl
        import struct
        victim = self.source / 'nested/b.jpg'
        entries = [(1, 6, 0xffffffff), (2, 4, 12345), (4, 4, 0xffffffff),
                   (16, 4, 0xffffffff), (32, 0, 0xffffffff)]
        acl = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', *e) for e in entries)
        os.setxattr(victim, 'system.posix_acl_access', acl)
        code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertIn('unsupported_metadata', str(records))
        self.assertFalse(self.dest.exists())
        os.removexattr(victim, 'system.posix_acl_access')
        fd = os.open(victim, os.O_RDONLY)
        try:
            flags = array.array('I', [0])
            fcntl.ioctl(fd, 0x80086601, flags, True)
            original = flags[0]
            flags[0] |= 0x40  # FS_NODUMP_FL
            fcntl.ioctl(fd, 0x40086602, flags, True)
            code, records = self.run_move()
            self.assertEqual(code, 1)
            self.assertIn('unsupported_inode', str(records))
            self.assertFalse(self.dest.exists())
        finally:
            flags[0] = original
            fcntl.ioctl(fd, 0x40086602, flags, True)
            os.close(fd)

    def test_unsupported_no_replace_link_retains_source(self):
        before = tree(self.source)
        with patch('dup_media.relocate.os.link', side_effect=OSError(errno.EOPNOTSUPP, 'synthetic publication unsupported')):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual(tree(self.source), before)
        self.assertFalse((self.dest / 'nested/b.jpg').exists())

    def test_inode_alias_held_on_second_filesystem(self):
        with tempfile.TemporaryDirectory(dir=os.environ['MOVE_CROSS_ROOT']) as t:
            self.dest = Path(t) / 'dest'
            os.link(self.source / 'a.jpg', self.source / 'hard.jpg')
            code, records = self.run_move()
            self.assertEqual(code, 0, records)
            self.assertEqual((self.dest / 'hard.jpg').read_bytes(), b'a' * 100)
            self.assertEqual((self.source / 'a.jpg').read_bytes(), b'a' * 100)

    def test_bind_mount_alias_and_nested_mount_are_rejected(self):
        from dup_media.move_fs import mounts
        alias = self.base / 'alias'
        alias.mkdir()
        subprocess.run(['mount', '--bind', str(self.source / 'nested'), str(alias)], check=True)
        try:
            with self.assertRaises((MoveError, ValueError)):
                mounts([Location(self.source), Location(alias)])
        finally:
            subprocess.run(['umount', str(alias)], check=True)
        nested = self.source / 'mount'
        nested.mkdir()
        subprocess.run(['mount', '-t', 'tmpfs', '-o', 'size=1m', 'tmpfs', str(nested)], check=True)
        try:
            with self.assertRaises(MoveError):
                mounts([Location(self.source), Location(self.dest)])
        finally:
            subprocess.run(['umount', str(nested)], check=True)

    def test_destination_parent_replaced_after_publish_blocks_source_removal(self):
        def replace(stage, path):
            if stage == 'before_unlink':
                (self.dest / 'nested').rename(self.dest / 'old-nested')
                (self.dest / 'nested').mkdir()
        with patch('dup_media.relocate.checkpoint', replace):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertEqual((self.dest / 'old-nested/b.jpg').read_bytes(), b'a' * 100)

    def test_case_alias_and_fsync_failure_do_not_erase_sources(self):
        (self.source / 'nested/B.JPG').write_bytes(b'a' * 100)
        code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertIn('destination_name_alias', str(records))
        self.assertFalse(self.dest.exists())
        (self.source / 'nested/B.JPG').unlink()
        before = tree(self.source)
        with patch('dup_media.relocate.os.fsync', side_effect=OSError(errno.EIO, 'synthetic sync failure')):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual(tree(self.source), before)

    def test_advisory_lock_blocks_second_writer(self):
        import fcntl
        from dup_media.scan import DIR_FLAGS
        fd = os.open(self.source, DIR_FLAGS)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            code, records = self.run_move()
            self.assertEqual(code, 1)
            self.assertEqual(records[-1]['moved'], 0)
            self.assertFalse(self.dest.exists())
        finally:
            os.close(fd)

    def test_late_in_place_source_or_destination_changes_are_detected(self):
        def change_source(stage, path):
            if stage == 'before_unlink':
                (self.source / path).write_bytes(b'z' * 100)
        with patch('dup_media.relocate.checkpoint', change_source):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'z' * 100)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
        # Restore duplicate fixture, select independent new destinations/journal.
        (self.source / 'nested/b.jpg').write_bytes(b'a' * 100)
        self.dest = self.base / 'second-dest'
        self.journal = self.base / 'second-journal'
        def change_destination(stage, path):
            if stage == 'before_unlink':
                (self.dest / path).write_bytes(b'z' * 100)
        with patch('dup_media.relocate.checkpoint', change_destination):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual((self.source / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertEqual((self.source / 'a.jpg').read_bytes(), b'a' * 100)

    def test_existing_empty_destination_and_nested_parents_succeed(self):
        (self.dest / 'nested').mkdir(parents=True)
        code, records = self.run_move()
        self.assertEqual(code, 0, records)
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertFalse((self.source / 'nested/b.jpg').exists())

    def test_unlink_to_journal_commit_gap_is_recoverable(self):
        from dup_media.move_journal import Journal
        original = Journal.state
        def fail(journal, path, state, *args, **kwargs):
            if state == 'source_removed':
                raise sqlite3.OperationalError('synthetic commit failure after physical unlink')
            return original(journal, path, state, *args, **kwargs)
        with patch.object(Journal, 'state', fail):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertFalse((self.source / 'nested/b.jpg').exists())
        self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
        self.assertEqual((self.source / 'a.jpg').read_bytes(), b'a' * 100)
        with sqlite3.connect(self.journal / 'journal.sqlite') as db:
            state, source_sig, keeper_sig, digest = db.execute('SELECT state,source_signature,keeper_signature,sha256 FROM items').fetchone()
            self.assertEqual(state, 'destination_verified')
            self.assertTrue(source_sig and keeper_sig and len(digest) == 64)

    def test_partial_batch_stops_after_second_victim_error(self):
        for name in ['b.jpg', 'c.jpg', 'd.jpg']:
            (self.source / name).write_bytes(b'a' * 100)
        def fail(stage, path):
            if stage == 'before_copy' and path == 'c.jpg':
                raise OSError('synthetic second victim failure')
        with patch('dup_media.relocate.checkpoint', fail):
            code, records = self.run_move()
        self.assertEqual(code, 1)
        self.assertEqual(records[-1]['moved'], 1)
        self.assertFalse((self.source / 'b.jpg').exists())
        self.assertEqual((self.dest / 'b.jpg').read_bytes(), b'a' * 100)
        for name in ['a.jpg', 'c.jpg', 'd.jpg', 'nested/b.jpg']:
            self.assertEqual((self.source / name).read_bytes(), b'a' * 100)
        self.assertFalse((self.dest / 'c.jpg').exists())

    def test_volatile_filesystem_is_not_an_archive_destination(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
            self.dest = Path(t) / 'dest'
            code, records = self.run_move()
            self.assertEqual(code, 1)
            self.assertIn('unsupported_filesystem', str(records))
            self.assertFalse(self.dest.exists())
            self.assertTrue((self.source / 'nested/b.jpg').exists())

    def test_copy_io_failure_retains_source_and_records_error(self):
        def fail(source, target):
            target.write(source.read(10))
            target.flush()
            raise OSError(errno.ENOSPC, 'synthetic write failure after partial staging copy')
        before = tree(self.source)
        with patch('dup_media.relocate.copy_stream', side_effect=fail) as fault:
            code, records = self.run_move()
            fault.assert_called_once()
        self.assertEqual(code, 1)
        self.assertEqual(tree(self.source), before)
        self.assertFalse((self.dest / 'nested/b.jpg').exists())
        with sqlite3.connect(self.journal / 'journal.sqlite') as db:
            self.assertEqual(db.execute('SELECT state,error FROM items').fetchone(), ('copying', 'io_failure'))

    def test_bind_mounted_scratch_alias_cannot_modify_either_tree(self):
        alias = self.base / 'scratch-alias'
        alias.mkdir()
        for owner in [self.source, self.dest]:
            owner.mkdir(exist_ok=True)
            holding = owner / 'holding'
            holding.mkdir()
            subprocess.run(['mount', '--bind', str(holding), str(alias)], check=True)
            try:
                before = holding.stat()
                with patch.dict(os.environ, {'TMPDIR': str(alias)}):
                    with self.assertRaises(ValueError):
                        self.run_move(dry=True)
                self.assertEqual(list(holding.iterdir()), [])
                self.assertEqual(holding.stat().st_mtime_ns, before.st_mtime_ns)
                self.assertEqual(holding.stat().st_ctime_ns, before.st_ctime_ns)
                self.assertFalse(self.journal.exists())
            finally:
                subprocess.run(['umount', str(alias)], check=True)

    def test_sqlite_spill_directory_is_pinned_outside_both_trees(self):
        self.dest.mkdir()
        before_source = self.source.stat()
        before_dest = self.dest.stat()
        original = Scan.run
        def spill(scan):
            original(scan)
            self.assertEqual(scan.db.execute('PRAGMA temp_store_directory').fetchone(), (scan.temp.name,))
            scan.db.execute('CREATE TABLE spill(value TEXT)')
            scan.db.executemany('INSERT INTO spill VALUES (?)', (('x' * 1024 + str(i),) for i in range(12000)))
            self.assertEqual(sum(1 for _ in scan.db.execute('SELECT value FROM spill ORDER BY substr(value,1000)')), 12000)
        with patch.dict(os.environ, {'SQLITE_TMPDIR': str(self.dest)}), patch.object(Scan, 'run', spill):
            code, records = self.run_move(dry=True)
        self.assertEqual(code, 0, records)
        self.assertEqual(list(self.dest.iterdir()), [])
        self.assertEqual(self.source.stat().st_mtime_ns, before_source.st_mtime_ns)
        self.assertEqual(self.dest.stat().st_mtime_ns, before_dest.st_mtime_ns)
        self.assertEqual(self.dest.stat().st_ctime_ns, before_dest.st_ctime_ns)

    def test_project_id_is_rejected_instead_of_lost(self):
        import array
        import fcntl
        from tests.move_fixtures import make_tree
        with tempfile.TemporaryDirectory(dir=os.environ['MOVE_CROSS_ROOT']) as t:
            self.source = Path(t) / 'source'
            make_tree(self.source)
            victim = self.source / 'nested/b.jpg'
            fd = os.open(victim, os.O_RDONLY)
            try:
                project = array.array('I', [0] * 7)
                fcntl.ioctl(fd, 0x801c581f, project, True)
                project[3] = 123
                fcntl.ioctl(fd, 0x401c5820, project, True)
            finally:
                os.close(fd)
            code, records = self.run_move()
            self.assertEqual(code, 1, records)
            self.assertIn('unsupported_project_metadata', str(records))
            self.assertTrue(victim.exists())
            self.assertFalse(self.dest.exists())
