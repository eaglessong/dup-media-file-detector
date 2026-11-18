"""Exercise scaffold preservation, path boundaries, and completion gates."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
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

    def context(self, role):
        values = {"repo_root": str(self.root), "feature_description": "Add bounded progress",
                  "touched_paths": ["dup_media/scan.py"],
                  "knowledge_map": "docs/forge/references/knowledge-map.md",
                  "evidence_digest": {"design": "docs/design/example.md", "head": "recorded-sha"}}
        return {key: values[key] for key in forge.PROMPT_INPUTS[role]}

    def test_all_role_prompts_bind_without_unresolved_tokens(self):
        for role in forge.PROMPT_INPUTS:
            with self.subTest(role=role):
                rendered = forge.render_prompt(self.root, role, self.context(role))
                self.assertIsNone(forge.TOKEN.search(rendered))
                self.assertIn(str(self.root), rendered)
                self.assertIn(
                    f"](<{self.root.resolve()}/docs/forge/references/prompt-contract.md>)", rendered
                )
                self.assertNotIn("](../references/", rendered)
                self.assertIn("dup_media/scan.py" if role in
                              ("code-archaeologist", "architecture-mapper", "scale-analyst",
                               "test-landscape-mapper", "prospect-devils-advocate")
                              else "recorded-sha", rendered)

    def test_prompt_binding_rejects_bad_context_and_unknown_role(self):
        role = "architecture-mapper"
        good = self.context(role)
        bad = [None, {}, {**good, "surprise": "value"},
               {**good, "feature_description": " "}, {**good, "repo_root": None},
               {**good, "repo_root": ["not-a-path"]}, {**good, "feature_description": {}},
               {**good, "touched_paths": "not-a-list"}, {**good, "touched_paths": [""]},
               {**good, "knowledge_map": "{{unbound}}"}]
        for context in bad:
            with self.subTest(context=context), self.assertRaises(ValueError):
                forge.render_prompt(self.root, role, context)
        with self.assertRaises(ValueError):
            forge.render_prompt(self.root, "../../escape", good)

    def test_broken_prompt_contract_and_missing_material_fail_check(self):
        prompt = self.root / "docs/forge/prompts/architecture-mapper.md"
        original = prompt.read_text()
        for broken in (original.replace("{{repo_root}}", "unbound root"),
                       original + "\n{{undeclared}}", original + "\n{{ bad syntax }}"):
            with self.subTest(broken=broken[-40:]):
                prompt.write_text(broken)
                self.assertTrue(forge.check(self.root))
                with self.assertRaises(ValueError):
                    forge.render_prompt(self.root, "architecture-mapper", self.context("architecture-mapper"))
        prompt.write_text(original)
        reference = self.root / "docs/forge/references/test-data-protocol.md"
        reference.unlink()
        errors = "\n".join(forge.check(self.root))
        self.assertIn("Missing required file: docs/forge/references/test-data-protocol.md", errors)
        self.assertIn("missing or unsafe material link", errors)

    def test_render_prompt_cli_success_and_rejection(self):
        context = self.root / "context.json"
        context.write_text(json.dumps(self.context("architecture-mapper")))
        command = [sys.executable, str(SOURCE / "scripts/forge.py"), "render-prompt",
                   "architecture-mapper", "--context", str(context)]
        result = subprocess.run(command, cwd=SOURCE, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.root), result.stdout)
        self.assertIsNone(forge.TOKEN.search(result.stdout))
        for invalid in ("{}", "not JSON"):
            context.write_text(invalid)
            result = subprocess.run(command, cwd=SOURCE, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_rendered_support_links_survive_spaces_and_parentheses(self):
        with tempfile.TemporaryDirectory() as external:
            checkout = Path(external) / "checkout (with spaces)"
            shutil.copytree(self.root, checkout)
            context = self.context("architecture-mapper")
            context["repo_root"] = str(checkout)
            rendered = forge.render_prompt(checkout, "architecture-mapper", context)
            contract = checkout.resolve() / "docs/forge/references/prompt-contract.md"
            self.assertTrue(contract.is_file())
            self.assertIn(f"](<{contract}>)", rendered)
            self.assertNotIn(f"]({contract})", rendered)

    def test_links_cannot_escape_repository(self):
        prompt = self.root / "docs/forge/prompts/architecture-mapper.md"
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external) / "outside.md"
            outside.write_text("Existing file outside the repository")
            relative = os.path.relpath(outside, prompt.parent)
            prompt.write_text(prompt.read_text() + f"\n[escape]({relative})\n")
            self.assertIn("missing or unsafe material link", "\n".join(forge.check(self.root)))
            with self.assertRaises(ValueError):
                forge.render_prompt(self.root, "architecture-mapper", self.context("architecture-mapper"))
            prompt.write_text(prompt.read_text().replace(relative, "outside-link.md"))
            (prompt.parent / "outside-link.md").symlink_to(outside)
            self.assertIn("missing or unsafe material link", "\n".join(forge.check(self.root)))
            with self.assertRaises(ValueError):
                forge.render_prompt(self.root, "architecture-mapper", self.context("architecture-mapper"))

    def test_design_only_delivery_is_distinct_from_implementation_completion(self):
        forge.new_feature(self.root, "example")
        self.status(phase="design-delivered")
        self.assertEqual(forge.check(self.root), [])
        self.status(phase="complete")
        self.assertIn("completion missing passing scopes", "\n".join(forge.check(self.root)))

    def test_patrol_materials_are_required_linked_and_mirrored(self):
        skill = self.root / ".claude/skills/patrol/SKILL.md"
        skill.write_text(skill.read_text() + "\nChanged\n")
        self.assertIn("patrol skill entry points must be identical.", forge.check(self.root))
        protocol = self.root / "docs/patrol/sweep.md"
        protocol.write_text(protocol.read_text() + "\n[Missing](absent.md)\n")
        self.assertTrue(any("absent.md" in error for error in forge.check(self.root)))
        protocol.unlink()
        self.assertIn("Missing required file: docs/patrol/sweep.md", forge.check(self.root))

    def test_ship_it_materials_are_required_linked_and_mirrored(self):
        skill = self.root / ".claude/skills/ship-it/SKILL.md"
        skill.write_text("divergent ship instructions")
        self.assertIn("ship-it skill entry points must be identical.", forge.check(self.root))
        playbook = self.root / "docs/ship-it/iteration-playbook.md"
        playbook.unlink()
        errors = "\n".join(forge.check(self.root))
        self.assertIn("Missing required file: docs/ship-it/iteration-playbook.md", errors)
        self.assertIn("missing or unsafe material link", errors)

    def test_review_skill_is_required_and_mirrored(self):
        skill = self.root / ".claude/skills/code-review/SKILL.md"
        skill.write_text("divergent review instructions")
        self.assertIn("code-review skill entry points must be identical.", forge.check(self.root))
        skill.unlink()
        self.assertIn("Missing required file: .claude/skills/code-review/SKILL.md", forge.check(self.root))

    def test_missing_artifact_and_divergent_skills(self):
        (self.root / "AGENTS.md").unlink()
        (self.root / ".claude/skills/forge/SKILL.md").write_text("different")
        errors = "\n".join(forge.check(self.root))
        self.assertIn("Missing required file: AGENTS.md", errors)
        self.assertIn("must be identical", errors)


if __name__ == "__main__":
    unittest.main()
