"""Standard-library feature scaffolding and structural evidence validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
PROSPECT_INPUTS = ("repo_root", "feature_description", "touched_paths", "knowledge_map")
ASSAY_INPUTS = ("repo_root", "evidence_digest", "knowledge_map")
PROMPT_INPUTS = {
    **dict.fromkeys(("code-archaeologist", "architecture-mapper", "scale-analyst",
                     "test-landscape-mapper", "prospect-devils-advocate"), PROSPECT_INPUTS),
    **dict.fromkeys(("devils-advocate", "scale-stress-reviewer",
                     "telemetry-security-reviewer", "test-realism-auditor"), ASSAY_INPUTS),
}
FORGE_REFERENCES = (
    "prompt-contract", "knowledge-map", "decision-records", "test-data-protocol",
    "live-capture-protocol", "shortcut-resistance",
)
PHASES = {"prospect", "survey", "smelt", "forge", "temper", "assay", "stamp", "complete", "blocked", "design-delivered"}
SCOPES = {"framework", "application", "integration", "e2e"}
REQUIRED = (
    "README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "docs/PRODUCT.md",
    "docs/WORKFLOW.md", "docs/templates/brief.md", "docs/templates/design.md",
    "docs/templates/evidence.md", "docs/templates/adr.md", "docs/design/first-scan.md",
    ".agents/skills/forge/SKILL.md", ".claude/skills/forge/SKILL.md",
    ".github/workflows/framework.yml", ".github/PULL_REQUEST_TEMPLATE.md",
    ".agents/skills/code-review/SKILL.md", ".claude/skills/code-review/SKILL.md",
    "docs/code-review/roles.md", "docs/code-review/report.md", "docs/forge/PORTING.md",
    ".agents/skills/ship-it/SKILL.md", ".claude/skills/ship-it/SKILL.md",
    "docs/ship-it/iteration-playbook.md", "docs/ship-it/state-and-evidence.md",
    "docs/ship-it/PORTING.md", "scripts/ship_it.py",
    ".agents/skills/patrol/SKILL.md", ".claude/skills/patrol/SKILL.md",
    "docs/patrol/sweep.md",
) + tuple(f"docs/forge/prompts/{role}.md" for role in PROMPT_INPUTS) + tuple(
    f"docs/forge/references/{name}.md" for name in FORGE_REFERENCES
)



def new_feature(root: Path, slug: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", slug) or len(slug) > 64:
        raise ValueError("Use a lowercase hyphenated slug of at most 64 characters.")
    folder = root / "work-items" / slug
    if folder.exists():
        raise ValueError(f"Feature already exists: {slug}; resume it instead.")
    title = slug.replace("-", " ").capitalize()
    # Read all templates before creating files; existing designs are preserved.
    content = {
        name: (root / f"docs/templates/{name}.md").read_text().replace("{title}", title)
        for name in ("brief", "design", "evidence")
    }
    design = root / f"docs/design/{slug}.md"
    folder.mkdir(parents=True)
    design.parent.mkdir(parents=True, exist_ok=True)
    for name in ("brief", "evidence"):
        (folder / f"{name}.md").write_text(content[name])
    if not design.exists():
        design.write_text(content["design"])
    status = {
        "schema_version": 1,
        "feature": slug,
        "kind": "application",
        "phase": "prospect",
        "design": f"docs/design/{slug}.md",
        "blockers": [],
        "verification": [],
        "review": {"mode": "pending", "evidence": "", "unresolved_blocking_findings": []},
    }
    (folder / "status.json").write_text(json.dumps(status, indent=2) + "\n")


def local_file(root: Path, value: object) -> bool:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return False
    candidate = (root / value).resolve()
    return candidate.is_relative_to(root.resolve()) and candidate.is_file()



def prompt_template(root: Path, role: str) -> str:
    if role not in PROMPT_INPUTS:
        raise ValueError(f"Unknown prompt role: {role}")
    template = (root / f"docs/forge/prompts/{role}.md").read_text()
    expected = set(PROMPT_INPUTS[role])
    actual = set(TOKEN.findall(template))
    if actual != expected:
        raise ValueError(f"{role}: template inputs differ: missing={sorted(expected - actual)}, "
                         f"unknown={sorted(actual - expected)}")
    remainder = TOKEN.sub("", template)
    if "{{" in remainder or "}}" in remainder:
        raise ValueError(f"{role}: malformed template placeholder")
    return template



def portable_prompt_links(root: Path, role: str, template: str) -> str:
    source_dir = root / "docs/forge/prompts"
    def replace(match: re.Match) -> str:
        target = match[2]
        if target.startswith(("https://", "http://", "#")):
            return match[0]
        path, separator, fragment = target.partition("#")
        candidate = (source_dir / path).resolve()
        if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
            raise ValueError(f"{role}: missing or unsafe prompt material link: {target}")
        destination = str(candidate) + (separator + fragment if separator else "")
        return match[1] + "<" + destination + ">" + match[3]
    return re.sub(r"(\[[^\]\n]*\]\()([^)\s]+)(\))", replace, template)


def render_prompt(root: Path, role: str, context: object) -> str:
    template = prompt_template(root, role)
    expected = set(PROMPT_INPUTS[role])
    if not isinstance(context, dict) or set(context) != expected:
        actual = set(context) if isinstance(context, dict) else set()
        raise ValueError(f"{role}: context inputs differ: missing={sorted(expected - actual)}, "
                         f"unknown={sorted(actual - expected)}")
    for key, value in context.items():
        if not isinstance(value, (str, list, dict)) or not value or (
            isinstance(value, str) and not value.strip()
        ):
            raise ValueError(f"{role}: input {key} must be a nonempty string, list, or object")
        if key in ("repo_root", "feature_description") and not isinstance(value, str):
            raise ValueError(f"{role}: input {key} must be a nonempty string")
        if key == "touched_paths" and (
            not isinstance(value, list) or
            any(not isinstance(path, str) or not path.strip() for path in value)
        ):
            raise ValueError(f"{role}: touched_paths must be a nonempty list of path strings")
    template = portable_prompt_links(root, role, template)
    rendered = TOKEN.sub(lambda match: context[match[1]] if isinstance(context[match[1]], str)
                         else json.dumps(context[match[1]], indent=2), template)
    if TOKEN.search(rendered):
        raise ValueError(f"{role}: unresolved placeholder in rendered prompt/context")
    return rendered


def check_forge_materials(root: Path) -> list[str]:
    errors = []
    for role in PROMPT_INPUTS:
        try:
            prompt_template(root, role)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    # Validate portable relative Markdown links in the workflow/skills/shared materials.
    materials = [name for name in REQUIRED if name.startswith(("docs/forge/", "docs/ship-it/", "docs/patrol/"))]
    materials += ["docs/WORKFLOW.md", ".agents/skills/forge/SKILL.md",
                  ".claude/skills/forge/SKILL.md", ".agents/skills/ship-it/SKILL.md",
                  ".claude/skills/ship-it/SKILL.md", ".agents/skills/patrol/SKILL.md",
                  ".claude/skills/patrol/SKILL.md"]
    for name in materials:
        source = root / name
        if not source.is_file():
            continue
        for target in re.findall(r"\[[^\]\n]*\]\(([^)\s]+)\)", source.read_text()):
            if target.startswith(("https://", "http://", "#")):
                continue
            path = target.split("#", 1)[0]
            candidate = (source.parent / path).resolve()
            if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
                errors.append(f"{name}: missing or unsafe material link: {target}")
    return errors


def check(root: Path) -> list[str]:
    errors = check_forge_materials(root)
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append(f"Missing required file: {name}")
    for skill in ("forge", "code-review", "ship-it", "patrol"):
        a = root / f".agents/skills/{skill}/SKILL.md"
        b = root / f".claude/skills/{skill}/SKILL.md"
        if a.is_file() and b.is_file() and a.read_bytes() != b.read_bytes():
            errors.append(f"{skill} skill entry points must be identical.")
    for folder in sorted((root / "work-items").iterdir()):
        if not folder.is_dir():
            continue
        label = f"work-items/{folder.name}"
        for name in ("brief.md", "evidence.md", "status.json"):
            if not (folder / name).is_file():
                errors.append(f"{label}: missing {name}")
        try:
            data = json.loads((folder / "status.json").read_text())
        except (OSError, ValueError) as exc:
            errors.append(f"{label}: unreadable status: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{label}: status must be an object")
            continue
        def fail(message: str) -> None:
            errors.append(f"{label}: {message}")
        if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            fail("schema_version must be 1")
        if data.get("feature") != folder.name:
            fail("feature must match folder name")
        phase = data.get("phase")
        if not isinstance(phase, str) or phase not in PHASES:
            fail("invalid phase")
        if data.get("kind") not in ("application", "documentation"):
            fail("kind must be application or documentation")
        if not local_file(root, data.get("design")):
            fail("design must reference an existing file inside the repository")
        blockers = data.get("blockers")
        if not isinstance(blockers, list) or any(not isinstance(x, str) or not x.strip() for x in blockers):
            fail("blockers must be a list of nonempty strings")
        if phase == "blocked" and not blockers:
            fail("blocked phase needs a concrete blocker")
        if phase == "complete" and blockers:
            fail("complete feature has blockers")
        runs = data.get("verification")
        if not isinstance(runs, list):
            fail("verification must be a list")
            runs = []
        passed = set()
        for run in runs:
            if not isinstance(run, dict):
                fail("verification entry must be an object")
                continue
            scope = run.get("scope")
            outcome = run.get("outcome")
            code = run.get("exit_code")
            valid_scope = isinstance(scope, str) and scope in SCOPES
            valid_outcome = isinstance(outcome, str) and outcome in {"passed", "failed", "blocked"}
            if not isinstance(run.get("command"), str) or not run["command"].strip():
                fail("verification needs a command")
            if not valid_scope or not valid_outcome:
                fail("invalid verification scope or outcome")
            if code is not None and type(code) is not int:
                fail("exit_code must be an integer or null")
            if outcome == "passed" and (type(code) is not int or code != 0):
                fail("passing verification needs exit_code 0")
            elif outcome == "passed" and valid_scope:
                passed.add(scope)
            if phase == "complete" and outcome != "passed":
                fail("complete feature has failed or blocked verification")
        review = data.get("review")
        if not isinstance(review, dict):
            fail("review must be an object")
            review = {}
        if phase == "complete":
            required = SCOPES if data.get("kind") == "application" else {"framework"}
            if required - passed:
                fail("completion missing passing scopes: " + ", ".join(sorted(required - passed)))
            if review.get("mode") not in ("independent", "self-review"):
                fail("completion needs an identified review mode")
            if not local_file(root, review.get("evidence")):
                fail("review evidence must reference an existing repository file")
            if review.get("unresolved_blocking_findings") != []:
                fail("completion requires zero unresolved blocking review findings")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    new = sub.add_parser("new-feature", help="create a brief, design, status, and evidence")
    new.add_argument("slug")
    render = sub.add_parser("render-prompt", help="bind a leaf-role prompt; does not dispatch")
    render.add_argument("role", choices=sorted(PROMPT_INPUTS))
    render.add_argument("--context", type=Path, required=True, help="JSON object with exact role inputs")
    sub.add_parser("check", help="validate framework structure and declared evidence")
    args = parser.parse_args()
    try:
        if args.action == "new-feature":
            new_feature(ROOT, args.slug)
            print(f"Created work-items/{args.slug}; edit its brief and docs/design/{args.slug}.md")
            return 0
        if args.action == "render-prompt":
            context = json.loads(args.context.read_text())
            print(render_prompt(ROOT, args.role, context), end="")
            return 0
        errors = check(ROOT)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if not errors:
        print("Framework structure and declared evidence are valid (not behavioral proof).")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
