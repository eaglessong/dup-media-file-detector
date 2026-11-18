# code_review port — evidence

## Source and adaptation

Read Cowork's aether-review skill and its specialist reviewer definitions. Preserved
local input modes, role routing, Devil's Advocate, E/I/R/D grounding and synthesized
reports. Removed organization-specific hostnames, deployment/telemetry dependencies,
people, bot identities, approval routing and fixed monorepo thresholds/policies.
Adapted roles to the current Python/POSIX/SQLite scanner and framework rules.

## Decisions and implementation

See docs/design/code-review-port.md. Paired skills link shared role/report contracts.
AGENTS/CLAUDE/README/WORKFLOW describe invocation and ASSAY integration. Framework
validation now checks both paired skills; a regression test removes/changes the review
skill and verifies validation fails. Corrected stale AGENTS application-stack wording.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/forge.py check`: exit 0.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`: eight tests, exit 0.
- `git diff --check`: exit 0.
- Skill-creator validator: installed its missing PyYAML dependency only in a temporary
  directory, not this project. The exact requested `code_review` name fails its hyphen
  convention. Temporary copies with only the name normalized pass every remaining
  check for both entry points. This is a documented naming exception, not an unqualified
  validator pass. Live command discovery in Codex/Claude clients was not exercised.

## Behavioral forward-test

An independent subagent received only the installed skill, shared references and an
isolated synthetic Git repository with a working diff. It correctly selected Full,
used the required sequential fallback (delegation prohibited in the fixture), pinned
and rechecked the diff snapshot, and identified the introduced external-file-symlink
read regression with file/line evidence. It did not flag a removed unused import or
present a pre-existing missing CLI as a newly introduced defect. It labelled unrun
verification, absent CI, and report-writing limits honestly. No target code/tests ran.
It reported a minor Quick-mode label inconsistency; normalized that wording.

This evaluates one local-diff scenario, not PR fetching, patch reconstruction, parallel
execution or all possible client integrations.

## Review and disposition

Separate self-review of the actual port checked source adaptation, read-only boundaries,
snapshot/base rules, reference paths, no hardcoded host/model/persona dependencies,
status and mirror enforcement. This is a review of newly written reviewer rules by
their author; do not claim independent review of the entire port. No unresolved
blocking findings. The independent pass above tested behavior on a synthetic diff.
Application code is unchanged; application integration/E2E suites were not rerun locally
for this framework change. GitHub application CI runs them on the PR.

## Delivery

Branch: codex/port-code-review. Owner review/merge remains separate. Resume by checking
the branch's GitHub PR and CI. The PR contains the final delivery URL and CI results.

## Owner-requested rename — 2026-11-18

USER: “rename the skill 'code_review' to 'code-review'”. Renamed both skill directories
and frontmatter, invocation docs, active forge/ship-it references, validator required
paths/mirror checks and existing validator tests. Historical evidence and verbatim
original USER quotes retain the old name. The design records the superseding request.
Branch: codex/rename-code-review, based on main; media-size-summary PR #5 is unchanged.

Checks: `python3 scripts/forge.py check` exited 0; `python3 -m unittest discover -s tests -v`
exited 0 (27 tests); `git diff --check` exited 0. All three mirrored skill pairs match.
Exact baseline comparison confirms both renamed SKILL.md bodies differ only by replacing
the old skill name; old directories are absent. Self-review checked maintained references,
preserved historical quotations, unchanged review authority and validator/test paths.
Standalone skill-creator quick_validate.py could not run under either system or bundled
Python because PyYAML is absent (exit 1); this is not recorded as a validation pass.
No application behavior or dependencies changed. No PR publication or merge performed.

## Rename PR and merge authorization — 2026-11-18

USER explicitly requested: “create a PR of the renaming and merge it”. This authorizes
this rename branch's ordinary merge, not media-size-summary PR #5 or a release.
At clean implementation head 80f48e68d68fdf24aad62cff18551302d334f9bd (base/merge-base
59f05d4a3160590f3b3e454130b879b07603b2b9), reran framework check, all 27 tests and diff
check: exit0. No application/CI/dependency change; existing hosted application checks
will still be required. Missing PyYAML standalone validator remains honestly unrun.

Used code-review Full: all five specialist checklists across three separate agents,
then a fourth agent challenged the draft. No human independence; some role passes
share agents. Review includes its own instructions, whose changes only rename the
command. Findings: draft0, retained0, advisory0; no fixes needed. Test-impact inspected
the one changed negative-test method: actual missing/divergent skill paths remain
discriminating. Final challenge examined stale-name/session retry and authority risks;
client discovery is untested with correct refresh/fallback guidance, not a claimed pass.
Local synthesis: .agent-local/reviews/rename-review-80f48e6.md. Reviewers did not run tests.

Ship-it will record exact PR/head/base/feedback/check provenance under ignored per-PR
state and require actual hosted success before a normal head-pinned merge. Branch-rules
API returned plan-related403; this is unknown policy information, not absence of rules.
No admin or rule bypass will be used. This entry adds delivery evidence only; skill,
validator and test content remain identical to the reviewed implementation.
