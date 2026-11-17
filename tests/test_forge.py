"""Exercise scaffold preservation, path boundaries, and completion gates."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("forge", SOURCE / "scripts/forge.py")
forge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forge)


class ForgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in forge.REQUIRED:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / name, target)
        (self.root / "work-items").mkdir()

    def status(self, **updates):
        path = self.root / "work-items/example/status.json"
        data = json.loads(path.read_text())
        data.update(updates)
        path.write_text(json.dumps(data))

    def test_scaffold_and_preserve_existing_design(self):
        design = self.root / "docs/design/example.md"
        design.write_text("Owner-authored design")
        forge.new_feature(self.root, "example")
        self.assertEqual(design.read_text(), "Owner-authored design")
        self.assertEqual(forge.check(self.root), [])
        with self.assertRaises(ValueError):
            forge.new_feature(self.root, "example")
        self.assertEqual(design.read_text(), "Owner-authored design")

    def test_reject_unsafe_slugs_before_writes(self):
        for slug in ("../escape", "/tmp/escape", "bad/name", "-bad", "Mixed", "a" * 65):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                forge.new_feature(self.root, slug)
        self.assertEqual(list((self.root / "work-items").iterdir()), [])

    def test_completion_requires_real_scopes_and_review(self):
        forge.new_feature(self.root, "example")
        self.status(phase="complete")
        errors = "\n".join(forge.check(self.root))
        self.assertIn("completion missing passing scopes", errors)
        self.assertIn("review mode", errors)
        runs = [{"scope": scope, "command": "actual-command", "exit_code": 0,
                 "outcome": "passed"} for scope in sorted(forge.SCOPES)]
        self.status(verification=runs, review={"mode": "self-review",
                    "evidence": "work-items/example/evidence.md",
                    "unresolved_blocking_findings": []})
        self.assertEqual(forge.check(self.root), [])
        runs[0]["exit_code"] = 1
        self.status(verification=runs)
        self.assertIn("passing verification needs exit_code 0", "\n".join(forge.check(self.root)))

    def test_path_escape_and_blockers_fail_validation(self):
        forge.new_feature(self.root, "example")
        self.status(design="../outside.md", phase="blocked")
        errors = "\n".join(forge.check(self.root))
        self.assertIn("inside the repository", errors)
        self.assertIn("concrete blocker", errors)
        outside = self.root.parent / "outside.md"
        self.assertFalse(forge.local_file(self.root, str(outside)))

    def test_malformed_status_is_reported_without_crashing(self):
        forge.new_feature(self.root, "example")
        for update in ({"phase": []}, {"verification": [None]}, {"review": []},
                       {"verification": [{"scope": [], "outcome": []}]},
                       {"blockers": "reason"}):
            with self.subTest(update=update):
                self.status(**update)
                self.assertTrue(forge.check(self.root))

    def test_review_skill_is_required_and_mirrored(self):
        skill = self.root / ".claude/skills/code_review/SKILL.md"
        skill.write_text("divergent review instructions")
        self.assertIn("code_review skill entry points must be identical.", forge.check(self.root))
        skill.unlink()
        self.assertIn("Missing required file: .claude/skills/code_review/SKILL.md", forge.check(self.root))

    def test_missing_artifact_and_divergent_skills(self):
        (self.root / "AGENTS.md").unlink()
        (self.root / ".claude/skills/forge/SKILL.md").write_text("different")
        errors = "\n".join(forge.check(self.root))
        self.assertIn("Missing required file: AGENTS.md", errors)
        self.assertIn("must be identical", errors)


if __name__ == "__main__":
    unittest.main()
