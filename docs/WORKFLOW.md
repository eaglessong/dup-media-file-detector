# Artifact-driven forge workflow

This workflow adapts Cowork's forge phases to a new local-media application. Scale the
amount of analysis to risk, keeping the evidence. A typo needs a direct edit and an
appropriate check; application behavior needs the full sequence. Run one feature per
branch/PR. The human supplies goals and constraints; the agent maintains execution artifacts.

## Inputs and ownership

`docs/PRODUCT.md` is product context. A feature uses `work-items/<slug>/brief.md`,
`docs/design/<slug>.md`, `work-items/<slug>/status.json`, and
`work-items/<slug>/evidence.md`. Product and safety decisions from the user outrank agent
assumptions. Accepted designs remain authoritative until explicitly revised. Capture
conflicts and consequential unanswered choices before implementation.

Start with `python3 scripts/forge.py new-feature <slug>`. Existing artifacts are never
overwritten. For an existing proposed design, the scaffolder preserves it. A brief
can be a few sentences; ask the agent to elaborate it from a conversation or GitHub issue.

## 1. PROSPECT — explore

Read the artifacts and repository before asking questions. Map the real entry points,
architecture, prior decisions, tests, filesystem boundaries, and delivery environment.
For a blank repo, say what does not exist. Identify uncertainty and representative
fixture needs. Record evidence with file paths/lines or commands, distinguishing facts
from assumptions. Do not pretend to have production scale or telemetry.

Test data gate: use generated temporary files for byte duplicates, different bytes,
empty files, Unicode names, inaccessible paths where supported, symlinks, and mutation
races. Actual decoding/similarity features need small licensed/synthetic valid media,
with source/license or generation recipe in `tests/fixtures/README.md`. Track missing
fixtures; a missing required environment or dataset blocks the affected completion claim.

## 1.5. SURVEY — clarify

Ask only consequential questions exploration could not answer. Confirm acceptance
criteria, boundaries, and destructive-operation constraints. Record the user's exact
choice as a USER ADR. Defaults selected by the agent are AGENT ADRs with rationale.
Proceed after material uncertainty is resolved; pause later only for a new material
ambiguity, necessary authority, or concrete blocker.

## 2. SMELT — design

Fill the design template before changing application behavior. Include current state,
numbered requirements, alternatives, recommendation, interfaces/data flow, file safety,
scale/cancellation, test strategy, rollout, and decisions. Compare realistic alternatives
when there is an architectural choice; do not pad trivial decisions. Map each requirement
to an intended test and demo outcome. Record open questions honestly. An agent may
write the design from the owner's prose. Design review can occur in the PR unless the
user explicitly requested a design approval checkpoint.

## 3. FORGE — implement

Implement the design in reviewable increments. Choose the stack through an ADR, then
add its reproducible setup and actual quality commands to `CONTRIBUTING.md` and CI.
Use bounded memory/I/O, clear errors and cancellation. Avoid changing source files in
a detection feature. Add safe diagnostic output without leaking private media paths
or content by default. If scope materially expands, revisit SURVEY/design.

## 4. TEMPER — verify

Run framework validation plus the actual application's format/lint/type/build checks
that apply. Test interactions with the real filesystem, and separately drive the
shipped entry point end to end using disposable fixtures. Check exact groups and
outputs, negative cases, error behavior, and preservation of original bytes. Unit
helpers alone do not prove a usable feature. Share representative fixture contracts
between integration and E2E tests where useful.

Record exact commands, exit codes, test assertions, environment, and limitations.
Missing tools and skipped checks are not passes. Update CI so required application
checks run on future PRs without personal credentials or media. Performance claims
require a reproducible workload and measurements; inferred scale stays an assumption.

## 5. ASSAY — challenge

Use `/code_review` (or ask the agent to follow `.agents/skills/code_review/SKILL.md`)
for the specialist review and Devil's Advocate synthesis. This invocation is review-only:
return to forge afterward to implement fixes and rerun affected checks. It does not
replace TEMPER or grant authority to post, push, or merge. Quick review is only for
small non-semantic changes; use Full for application and framework behavior changes.

Review the final diff from correctness, usability, file safety/privacy, scale, and test
realism perspectives. Ask: can this test pass while the feature is broken; does it
exercise the actual entry point; can a scan escape its root or race a file change; are
approximate matches being presented as proof? Use an independent reviewer when
available/authorized; otherwise label a separate self-review pass explicitly.

Log each finding as FIXED, REFUTED (with evidence), or DEFERRED (with impact). Unresolved
correctness, data-loss, privacy, and missing-acceptance-test findings block completion.
Rerun affected checks after fixes. Do not silently downgrade a blocker.

## 6. STAMP — deliver

Update docs, all feature artifacts, and the requirement/test matrix. Record verification
runs in status.json (command, exit_code, outcome, scope); `scope` is `framework`,
`application`, `integration`, or `e2e`. A pass requires exit_code 0. For a complete
application feature, all four scopes must have passing evidence and no failed/blocked
runs. Remove superseded runs from the current status list; retain their history in the
evidence narrative. `kind: documentation` requires passing framework checks only.

Run `python3 scripts/forge.py check` and relevant tests. Review the diff for secrets and
unrelated changes. Fetch and check integration with current main when available; do
not destructively reset or rewrite a published branch. Create a PR using the template,
check GitHub CI, and handle review comments. Do not merge without user authority.

`phase: complete` means implemented, verified and reviewed, ready for owner review;
it does not mean merged or released. A blocked run uses `phase: blocked` and a specific
nonempty `blockers` list. On resume, read status/evidence and continue at the recorded
phase; avoid starting over. Finish with the PR URL (or local branch if offline), what
the user can try, decisions made, and any material limitation.

## What automation proves

The scaffolder creates consistent artifacts. CI checks required files, status schema,
references, synchronized skills, and declared completion evidence. These structural
checks cannot prove that a command was actually run, that assertions are meaningful,
or that a feature works. The executing agent records truthful evidence; behavioral
checks and PR review establish product correctness. GitHub does not execute a hosted
coding agent just because an issue was filed. No paid integration is configured.
