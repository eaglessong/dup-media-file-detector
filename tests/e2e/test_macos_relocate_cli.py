import json
import os
from pathlib import Path
import tempfile
from tests.macos_fixtures import MacFixture, set_attribute
from tests.e2e import test_relocate_cli as portable


class MacCli(MacFixture):
    cli = portable.MoveCli.cli
    test_shipped_cli_dry_run_then_execution_and_repeat = portable.MoveCli.test_shipped_cli_dry_run_then_execution_and_repeat
    test_destination_collision_and_extension_override = portable.MoveCli.test_destination_collision_and_extension_override
    test_entrypoint_sigint_and_sigkill_at_durable_transfer_boundaries = portable.MoveCli.test_entrypoint_sigint_and_sigkill_at_durable_transfer_boundaries
    test_shipped_cli_rejects_scratch_within_destination = portable.MoveCli.test_shipped_cli_rejects_scratch_within_destination
    test_shipped_cli_accepts_existing_empty_destination = portable.MoveCli.test_shipped_cli_accepts_existing_empty_destination

    def test_resource_fork_cli_refuses_and_reports_policy(self):
        set_attribute(self.source / 'nested/b.jpg', 'com.apple.ResourceFork', b'synthetic fork')
        for dry in [True, False]:
            result = self.cli(dry=dry)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(records[0]['metadata_policy'], 'macos-data-only')
            self.assertIn('resource_fork_unsupported', result.stdout)
            self.assertFalse(self.dest.exists())
            self.assertFalse(self.journal.exists())
            self.assertTrue((self.source / 'nested/b.jpg').exists())

    def test_real_cross_device_cli_move(self):
        cross = os.environ.get('MOVE_CROSS_ROOT')
        if not cross:
            if os.environ.get('REQUIRE_MAC_MOVE_TESTS') == '1':
                self.fail('second APFS filesystem is mandatory')
            self.skipTest('provide MOVE_CROSS_ROOT on a separate APFS filesystem')
        self.assertNotEqual(Path(cross).stat().st_dev, self.source.stat().st_dev)
        with tempfile.TemporaryDirectory(dir=cross) as t:
            self.dest = Path(t).resolve() / 'dest'
            result = self.cli()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((self.dest / 'nested/b.jpg').read_bytes(), b'a' * 100)
            self.assertFalse((self.source / 'nested/b.jpg').exists())
            self.assertEqual((self.source / 'a.jpg').read_bytes(), b'a' * 100)


class MacPermissionCli(MacFixture):
    def invoke(self, fixture, dry):
        import subprocess
        import sys
        args = [sys.executable, '-m', 'dup_media', '--move-duplicates', str(fixture.source),
                '--destination', str(fixture.dest)]
        args += ['--dry-run'] if dry else ['--journal', str(fixture.journal), '--exclusive-access']
        result = subprocess.run(args, cwd=portable.REPO, capture_output=True, text=True, timeout=30)
        return result, [json.loads(line) for line in result.stdout.splitlines()]

    def test_static_mode_acl_and_inheritance_block_before_any_cli_move(self):
        from tests.macos_fixtures import PERMISSION_CASES, namespace_snapshot, permission_tree
        self.assertNotEqual(os.geteuid(), 0, 'ordinary-user CLI contract')
        for case in PERMISSION_CASES:
            with self.subTest(case=case), permission_tree(case) as fixture:
                source_before = namespace_snapshot(fixture.source)
                dest_before = namespace_snapshot(fixture.dest) if fixture.dest.exists() else None
                all_before = namespace_snapshot(fixture.base)
                for dry in ((False,) if case.startswith('journal_') else (True, False)):
                    result, records = self.invoke(fixture, dry)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn(fixture.expected, result.stdout)
                    self.assertEqual(records[-1]['moved'], 0)
                    self.assertFalse(records[-1]['complete'])
                    self.assertEqual(namespace_snapshot(fixture.source), source_before)
                    self.assertEqual(namespace_snapshot(fixture.dest) if fixture.dest.exists() else None,
                                     dest_before)
                    self.assertFalse(fixture.journal.exists())
                    self.assertEqual(namespace_snapshot(fixture.base), all_before)

    def test_foreign_sticky_cli_refuses_and_preserves_every_original(self):
        from tests.macos_fixtures import namespace_snapshot, permission_tree
        self.assertNotEqual(os.geteuid(), 0)
        with permission_tree('sticky_foreign') as fixture:
            before = namespace_snapshot(fixture.source)
            for dry in (True, False):
                result, records = self.invoke(fixture, dry)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('source_permission_denied', result.stdout)
                self.assertEqual(records[-1]['moved'], 0)
                self.assertEqual(namespace_snapshot(fixture.source), before)
                self.assertFalse(fixture.dest.exists())
                self.assertFalse(fixture.journal.exists())

    def test_sticky_owner_and_acl_delete_grant_cli_succeed(self):
        from tests.macos_fixtures import permission_tree
        self.assertNotEqual(os.geteuid(), 0)
        for case in ('sticky_owner', 'acl_grants_delete', 'creation_acl'):
            with self.subTest(case=case), permission_tree(case) as fixture:
                result, records = self.invoke(fixture, True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(records[-1]['planned'], 2)
                result, records = self.invoke(fixture, False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(records[-1]['moved'], 2)
                self.assertEqual((fixture.source / 'c.jpg').read_bytes(), b'second exact group')
                self.assertEqual((fixture.dest / 'zz-blocked/second.jpg').read_bytes(), b'second exact group')
                self.assertFalse((fixture.source / 'zz-blocked/second.jpg').exists())
