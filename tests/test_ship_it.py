"""Exercise durable modes, attempt bounds, stale evidence and atomic state writes."""
import fcntl
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ship_it", SOURCE / "scripts/ship_it.py")
ship = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ship)
HEAD, BASE, NEXT, MERGE = (character * 40 for character in "abcd")


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "run/state.json"

    def init(self, **kwargs):
        return ship.initialize(self.path, "owner/repo", 12, HEAD, BASE, **kwargs)

    def verify(self, head=HEAD, base=BASE, code=0):
        return ship.apply(self.path, "verify", {"head": head, "base": base,
                          "source": "execution", "commands": [{"command": "actual-recorded-command", "exit_code": code}]})

    def test_resume_preserves_history_rounds_mode_and_identity(self):
        self.init(no_merge=True, max_rounds=5)
        ship.apply(self.path, "round")
        ship.apply(self.path, "note", {"item": "review:1:v1", "disposition": "REFUTED"})
        ship.apply(self.path, "failure", signature="known-cause")
        before = ship.read(self.path)
        resumed = self.init(no_merge=False, max_rounds=20)
        self.assertEqual(resumed, before)
        self.assertTrue(resumed["no_merge"])
        with self.assertRaises(ValueError):
            ship.initialize(self.path, "other/repo", 12, HEAD, BASE)
        self.assertEqual(ship.read(self.path), before)
        self.verify()
        ship.apply(self.path, "finish", status="merge_ready")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            ship.apply(self.path, "finish", status="merged", merge_commit=MERGE)
        self.assertEqual(self.path.read_bytes(), before)

    def test_no_merge_rejects_merged_without_terminal_status_masking(self):
        self.init(no_merge=True)
        self.verify()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "persisted --no-merge"):
            ship.apply(self.path, "finish", status="merged", merge_commit=MERGE)
        self.assertEqual(self.path.read_bytes(), before)

    def test_head_or_base_changes_invalidate_verification(self):
        for head, base in ((NEXT, BASE), (HEAD, NEXT)):
            with self.subTest(head=head, base=base):
                self.init(new_run=True)
                self.verify()
                changed = ship.apply(self.path, "observe", {"head": head, "base": base,
                                                          "feedback_digest": "feedback-v2"})
                self.assertIsNone(changed["verified_head"])
                self.assertIsNone(changed["verified_base"])
                before = self.path.read_bytes()
                with self.assertRaises(ValueError):
                    self.verify()
                with self.assertRaises(ValueError):
                    ship.apply(self.path, "finish", status="merge_ready")
                self.assertEqual(self.path.read_bytes(), before)
                self.verify(head, base)
                result = ship.apply(self.path, "finish", status="merged", merge_commit=MERGE)
                self.assertEqual(result["merge_commit"], MERGE)

    def test_invalid_or_failed_verification_cannot_replace_state(self):
        self.init()
        before = self.path.read_bytes()
        for code in (1, None, False):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.verify(code=code)
            self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(ValueError):
            ship.apply(self.path, "verify", {"head": HEAD, "base": BASE, "commands": []})
        with self.assertRaises(ValueError):
            ship.apply(self.path, "observe", {"head": "not-sha", "base": BASE, "feedback_digest": "v1"})
        self.assertEqual(self.path.read_bytes(), before)

    def test_simulation_cannot_set_verified_refs(self):
        self.init()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "simulation"):
            ship.apply(self.path, "verify", {"head": HEAD, "base": BASE,
                       "source": "simulation", "commands": [{"command": "fixture", "exit_code": 0}]})
        self.assertEqual(self.path.read_bytes(), before)

    def test_missing_nullable_keys_are_controlled_cli_errors(self):
        original = self.init()
        for key in ("verified_head", "verified_base", "merge_commit", "feedback_digest"):
            for status in ("in_progress", "merge_ready", "merged"):
                with self.subTest(key=key, status=status):
                    state = dict(original, status=status)
                    del state[key]
                    self.path.write_text(json.dumps(state))
                    before = self.path.read_bytes()
                    result = subprocess.run([sys.executable, str(SOURCE / "scripts/ship_it.py"),
                                             "read", "--state", str(self.path)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("ERROR:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(self.path.read_bytes(), before)

    def test_caps_and_repeated_failures_block_without_reset(self):
        self.init(max_rounds=2)
        self.assertEqual(ship.apply(self.path, "round")["round"], 1)
        self.assertEqual(ship.apply(self.path, "round")["round"], 2)
        capped = ship.apply(self.path, "round")
        self.assertEqual((capped["round"], capped["status"]), (2, "blocked"))
        self.assertEqual(self.init(max_rounds=20), capped)
        with self.assertRaises(ValueError):
            ship.apply(self.path, "round")
        self.init(new_run=True)
        for attempt in range(1, 4):
            state = ship.apply(self.path, "failure", signature="same-ci-cause")
            self.assertEqual(state["failures"]["same-ci-cause"], attempt)
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(self.init(), state)

    def test_tighter_cap_cannot_discard_round_history(self):
        self.init(max_rounds=10)
        for _ in range(3):
            ship.apply(self.path, "round")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.init(max_rounds=2)
        self.assertEqual(self.path.read_bytes(), before)
        tightened = self.init(max_rounds=3)
        self.assertEqual((tightened["round"], tightened["max_rounds"], tightened["status"]),
                         (3, 3, "blocked"))
        self.assertEqual(self.init(max_rounds=20), tightened)

    def test_new_run_archives_old_mode_and_evidence(self):
        self.init(no_merge=True)
        ship.apply(self.path, "note", {"source": "prior authorization scope"})
        old = ship.read(self.path)
        new = self.init(new_run=True)
        self.assertFalse(new["no_merge"])
        self.assertEqual(new["round"], 0)
        archives = list(self.path.parent.glob("state.archived-*.json"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(ship.read(archives[0]), old)
        self.assertEqual(new["history"][0]["previous_state"], archives[0].name)

    def test_lock_contention_and_failed_replace_preserve_prior_state(self):
        self.init()
        before = self.path.read_bytes()
        with open(str(self.path) + ".lock", "r+") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            command = [sys.executable, str(SOURCE / "scripts/ship_it.py"), "round", "--state", str(self.path)]
            result = subprocess.run(command, cwd=SOURCE, capture_output=True, text=True)
            self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(self.path.read_bytes(), before)
        with patch.object(ship.os, "replace", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                ship.apply(self.path, "round")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob(".ship-it-*")), [])

    def test_cli_errors_and_corrupt_state_never_reset_silently(self):
        command = [sys.executable, str(SOURCE / "scripts/ship_it.py"), "init", "--state", str(self.path),
                   "--repo", "owner/repo", "--pr", "12", "--head", HEAD, "--base", BASE, "--no-merge"]
        result = subprocess.run(command, cwd=SOURCE, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["no_merge"])
        self.path.write_text("corrupt JSON")
        result = subprocess.run(command, cwd=SOURCE, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.path.read_text(), "corrupt JSON")


if __name__ == "__main__":
    unittest.main()
