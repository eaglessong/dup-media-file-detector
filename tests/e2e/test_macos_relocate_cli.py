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
