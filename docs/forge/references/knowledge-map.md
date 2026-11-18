# Project knowledge map

These are navigation hints, not evidence that current behavior is correct. Verify paths,
symbols, defaults and line numbers in the target checkout before citing them. Do not
import facts from this map into a finding without reading the implementation.

| Question | Starting point |
| --- | --- |
| Product intent and user decisions | docs/PRODUCT.md, docs/design/, docs/decisions/ |
| Agent authority and phase/evidence contract | AGENTS.md, CLAUDE.md, docs/WORKFLOW.md |
| Feature state/resumption | work-items/<slug>/brief.md, status.json, evidence.md |
| Real CLI and JSON/exit/error contract | dup_media/__main__.py, README.md, tests/test_application.py |
| Traversal, open flags, identity/signature checks | dup_media/scan.py and filesystem integration tests |
| SQLite/temp index, size/hash candidates, byte proof | dup_media/scan.py; trace consumers rather than assuming hash equality is proof |
| Filesystem tests and entry-point behavior | tests/integration/, tests/e2e/, tests/fixtures/README.md |
| Actual local checks/CI/platforms | CONTRIBUTING.md, .github/workflows/ |
| Scaffold, validation and prompt rendering | scripts/forge.py, tests/test_forge.py |
| Review roles, grounding and synthesized report | docs/code-review/, .agents/skills/code-review/SKILL.md |
| Forge role prompts and protocols | docs/forge/prompts/, docs/forge/references/ |

Current baseline is a local read-only exact-byte scanner, extension-based media
selection, root-relative JSON inventory, and explicit error/completeness/exit semantics.
Read accepted first-scan design/decisions for the actual contract, including symlinks,
hardlinks, empty files, platform limits, source mutation and output location. There is
no production telemetry service, token server, cloud deployment, GUI or licensed media
corpus required by this workflow. Future features must discover their actual dependencies.

For a changed/new path, search with rg and Git first. For external Python/SQLite/POSIX
claims, verify against the supported runtime and authoritative docs; source-level
platform assumptions are not proof a particular NAS supports them. Do not crawl private
media directories to discover workload size. Ask for aggregate workload descriptions.
