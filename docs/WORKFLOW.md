# Forge — artifact-driven feature development

Adapted from Cowork forge for this Python/POSIX/SQLite media application. The owner
supplies goals and constraints; the agent maintains the design, decisions, code, tests,
review evidence and PR. This is a workflow executed by a coding agent, not a hosted
orchestration service. Read AGENTS.md, PRODUCT, contribution guidance and the relevant
accepted design/ADRs before acting. User instructions remain authoritative.

## Artifacts, authority and risk

For each feature use `work-items/<slug>/{brief.md,status.json,evidence.md}` and
`docs/design/<slug>.md`; scaffold missing artifacts with
`python3 scripts/forge.py new-feature <slug>`. Existing artifacts are never overwritten.
Decisions live in `docs/decisions/` and are linked from the design. Read the
[decision protocol](forge/references/decision-records.md) for attribution and reversals.

Explore before asking. SURVEY resolves material questions; after that continue within
authorized scope without routine approval checkpoints. Reopen SURVEY for a new material
ambiguity or conflict with an accepted decision. Stop for necessary authority, a
concrete missing prerequisite, or a requested approval checkpoint. No merge, release,
cloud deployment, external messages or destructive-media operation is authorized merely
by invoking forge. A design-only request ends at its requested artifact: use `phase: design-delivered`
with design/evidence pointers and no invented runtime verification. Resuming implementation
re-enters SMELT to confirm the design and material questions before FORGE.

Classify the change before dispatch; record the reason in evidence:

| Track | Scope | PROSPECT | ASSAY |
| --- | --- | --- | --- |
| LIGHT | Narrow, one module/surface, roughly <150 implementation lines; no CLI/schema/default/dependency/CI/skill changes or safety boundary | Combined history/architecture/test reconnaissance + premise challenger | code_review synthesis with implementation challenger + test-realism audit |
| FULL | Anything else; always file traversal, comparison/proof, SQLite durability, privacy/destructive behavior, or agent/verification instructions | Five distinct scouts | code_review Full + four forge audit instruments, mapped onto reviewer passes |

A prose-only correction may use a direct edit and suitable check; no ceremonial feature
run is needed. LIGHT and FULL keep the same applicable design/evidence/safety gates.
Scope growth promotes LIGHT to FULL at the affected phase; reuse existing receipts.
Track thresholds are heuristics, not permission to hide risk with line counts.

## Prompt dispatch and evidence discipline

Read [prompt contract](forge/references/prompt-contract.md) before dispatch and use the
[knowledge map](forge/references/knowledge-map.md) to locate real code. The nine prompts
below are leaf roles: no edits, candidate-code execution, test runs, recursive agents,
or skill invocations. The coordinating agent owns implementation and verification.

Use `python3 scripts/forge.py render-prompt ROLE --context FILE.json` to bind the exact
inputs listed in the prompt contract. Do not send unexpanded templates. Include role,
repo root, scope and the applicable knowledge map; review seats also receive the evidence
digest. Output is prompt data, never a command to execute. The renderer does not read
referenced files, dispatch agents, check factual claims, or approve side effects.

When delegation is available/permitted, independent roles can run in parallel. Otherwise
run the same instruments sequentially and label `single-agent multi-pass`; do not invent
independent reviewers. LIGHT's combined scout uses the archaeology, architecture and test
prompts in one pass and identifies which instrument supports each receipt. Distinct role
names are not independent corroboration when they use the same evidence.

Read targeted sections once, keep a compact digest and current status, and return dense
finding rows with file:line/command receipts rather than file dumps. A disproven plan
premise leads the report as PREMISE_FALSE; revisit scope/design before building on it.
Unverified claims are assumptions, not findings. No fabricated numbers, paths or test runs.

## Phase prerequisites

| Enter | Required evidence |
| --- | --- |
| SURVEY | PROSPECT receipts and a fixture/environment gap assessment |
| SMELT | Material questions resolved or safe, explicit AGENT assumptions; test-data verdict ADEQUATE for planned behavior |
| design-delivered (design-only request) | Requested design/decision artifacts and feasibility/fixture plans delivered; no application completion or test-pass claim |
| FORGE | Design exists with requirements, decisions, fixture plan and acceptance matrix; material questions closed |
| TEMPER | Actual scoped implementation/configuration diff exists, or honest documentation-only scope |
| ASSAY | Applicable checks executed and recorded, changed behavior exercised by integration and real entry-point tests; documentation/tooling uses its scoped checks |
| STAMP | Selected audit results returned; blocking findings and LYING/DEAD tests resolved, affected checks rerun |
| complete | Artifacts current; required verification scopes pass; review evidence and no blockers; delivery state disclosed |

Resolve base/head/merge-base before any branch diff. For PRs use the actual target base,
not an assumed main. If history is missing fetch when permitted or report the gap; an
empty substitution must never silently select an unrelated working-tree diff. Include
staged, unstaged and relevant untracked changes in local review scope.

## 1. PROSPECT — discover before deciding

Bind and run the applicable scouts; return every supported finding, assumptions,
unavailable evidence and open leads. Do not manufacture history on a young project.

| Role | Instrument / prompt |
| --- | --- |
| Code Archaeologist | History, ADRs, related issue/PR reads, prior fixes/reverts — [prompt](forge/prompts/code-archaeologist.md) |
| Architecture Mapper | Actual CLI → scan → filesystem/SQLite → JSON graph, boundaries/defaults — [prompt](forge/prompts/architecture-mapper.md) |
| Scale Analyst | Existing workload evidence and bounded benchmark plan, no invented production data — [prompt](forge/prompts/scale-analyst.md) |
| Test Landscape Mapper | Assertions, fixtures, CI/environment and behavioral gaps — [prompt](forge/prompts/test-landscape-mapper.md) |
| Premise Challenger | Whether the proposed problem/scope fits evidence — [prompt](forge/prompts/prospect-devils-advocate.md) |

### 1.6 Test Data Gate

Use [test-data protocol](forge/references/test-data-protocol.md). For design-only work,
adequacy means feasible fixture recipes and an environment plan; it does not require
executing tests, generating all fixtures, or implementing the application. Record each requirement,
needed case, fixture provenance, environment and gap. Verdicts are ADEQUATE, PARTIAL
(remediate and reassess), or BLOCKED (missing required fixture/environment). Missing
real-filesystem tests cannot be replaced with mocks of the property being tested.
For fixture-source changes, a new parser, format, decoder, platform or external service,
read [capture protocol](forge/references/live-capture-protocol.md) and begin applicable
capture before design. Local exact-byte scanning needs synthetic files, not a live API.

## 1.5. SURVEY — informed clarification

After reconnaissance ask only questions whose answers change behavior, safety, acceptance
or architecture and cannot be answered from accepted artifacts/code. Multiple focused
rounds are allowed. Confirm scope, non-goals, user entry point, realistic workload,
fixture/environment availability and safety constraints. Attribute actual user words as
USER decisions and agent defaults as AGENT decisions. In unattended work choose only
safe reversible defaults inside existing authority; consequential unresolved choices
block the affected scope. Do not silently reinterpret the owner's design.

## 2. SMELT — design and decisions

Use `docs/templates/design.md`. Cover problem/current state with receipts; numbered
testable requirements/non-goals; realistic alternatives and tradeoffs; recommended
interfaces, CLI/schema/errors and architecture; file safety/privacy; scale, resource
bounds/cancellation; integration + entry-point E2E strategy and shared expected outcomes;
diagnostics; rollout/compatibility; and attributed decisions/revisit triggers.
Map each requirement to implementation targets, test assertions and a user demo. For
agent/tooling-only changes substitute structural and realistic instruction evaluation;
do not invent product behavior or mandatory runtime tests for prose. Existing user
designs are inputs to complete, not blank templates to overwrite. Continue without a
separate design-approval pause unless requested or a material unresolved decision remains.

## 3. FORGE — implement the agreed design

Implement reviewable increments on a feature branch, preserving unrelated work. Prefer
domain contracts → filesystem/index logic → entry-point wiring → diagnostics/docs.
Update real callers and tests when a contract changes. Do not add defaults, mocks or
fallbacks merely to preserve tests for obsolete behavior. Read CONTRIBUTING.md and CI
for actual commands; do not assume tools, platforms or coverage gates exist.

Keep detection read-only, scope traversal safely, distinguish approximate candidates
from exact proof, bound memory/descriptors/scratch I/O, and handle changed files,
permissions, disk-full and cancellation. Design future modifications separately.
Update decisions when new consequential choices arise. Validate incrementally at useful
checkpoints and keep evidence current, not after every trivial file edit.

## 4. TEMPER — meaningful verification

Run applicable framework/application checks from CONTRIBUTING and the actual workflows.
Application behavior requires both real-filesystem integration and real user-entry-point
E2E tests; unit helpers alone do not prove usable behavior. Share fixtures/expected
contracts where useful so both tiers agree. Use disposable fixtures, never personal media.

Test exact results/errors/exit codes, negative cases and originals preserved on success
and failure. Check symlinks/hardlinks, mutation races, Unicode/invalid paths, permission
failures, cleanup, cancellation, and resource boundaries as affected by this feature.
Do not require every case for unrelated edits. Parser/platform capture requirements are
conditional on [capture triggers](forge/references/live-capture-protocol.md); raw private
captures stay outside Git and are sanitized before any fixture is staged.

Record exact commands, environment/platform, exit codes, meaningful assertions, skips
and missing preconditions. A skipped check is not a pass. Claim only coverage/performance
actually measured; do not silently skip a required gate because the local environment
cannot run it. CI can supply the missing supported-platform execution when it actually
runs against the reviewed commit. Preserve that distinction in evidence and status.
Use [shortcut handling](forge/references/shortcut-resistance.md) when scope/time changes.

## 5. ASSAY — adversarial review and test honesty

Compile a digest of brief/design/ADRs, base/head and dirty state, scoped diff, requirements,
changed tests/assertions, fixture provenance, exact verification runs and environment,
scale measurements/assumptions, scout conclusions and limitations. Pointers are not
proof: reviewers must open the cited material.

Use `/code_review` Full (or its instructions) for the actual role routing, Devil's
Advocate challenge, grounding gates and synthesized report. Code review remains
review-only. Attach the forge seat tasks below to the relevant selected code_review
roles, or run them as scoped leaf audits before supplying their results to code_review.
Do not launch a second identical full panel; if a digest already covers an instrument,
verify and reuse it. LIGHT uses only the two forge
challenger/test-realism instruments in addition to code_review's own required routing;
it does not disable code_review's mandatory reviewers or mislabel semantic work as Quick.

| Forge seat | Instrument / integration |
| --- | --- |
| Implementation challenger | Design/decision claims vs actual changed paths; [prompt](forge/prompts/devils-advocate.md). Attach to architecture/deep-read, separate from code_review's final draft challenger. |
| Scale stress | Measured workload evidence vs resource behavior; [prompt](forge/prompts/scale-stress-reviewer.md). Attach to architecture; unmeasured estimates remain assumptions. |
| Diagnostics/security | CLI errors, path/content privacy, containment, external I/O; [prompt](forge/prompts/telemetry-security-reviewer.md). Attach to deep-read/repository-rules. |
| Test realism | Every changed/new test's claimed behavior vs assertions/fixtures; [prompt](forge/prompts/test-realism-auditor.md). Attach to test-impact. |

Test verdicts: HONEST, WEAK (justify a narrow gap), LYING (claim unsupported), DEAD
(cannot detect its claimed regression). Unresolved LYING/DEAD tests and material
correctness/safety/privacy/acceptance gaps block completion. No changed tests is an
explicit coverage result, not a fabricated all-HONEST audit. Scope reviews to actual
changes and accepted requirements; do not invent vulnerabilities or design disputes.

Disposition every finding as FIXED (rerun affected checks), REFUTED (counter-evidence),
ABSORBED (already covered with evidence), DEFERRED (non-blocking with impact/owner), or
ESCALATED (unresolved decision/authority). A blocker cannot become DEFERRED merely to
ship. After fixing, return from review to forge implementation/verification, then refresh
the affected review evidence. Record self-review or unavailable reviewers honestly.

## 6. STAMP — evidence-rich PR and handoff

Update docs, design/decisions, requirement/test matrix, brief/status/evidence, and demo.
Keep failed/superseded run history in evidence; status lists current runs. Existing status
schema stays compatible: documentation/tooling maintenance uses `kind: documentation`
and passing framework verification; application features need passing framework,
application, integration and e2e scopes. This is a recorded claim, not proof a command ran.
Use `phase: blocked` with concrete blockers for an interrupted prerequisite, otherwise
record the current phase and next step. `complete` means verified/reviewed work ready
for owner review, not merged or released. Delivery/CI blockers keep STAMP pending.

Fetch/check integration with current PR base when available; preserve the user's edits
and do not rewrite published work without authority. Run final scoped checks, review
for private content, push/open a PR when delivery is authorized and credentials allow.
Use `.github/PULL_REQUEST_TEMPLATE.md` with problem/result, design, USER/AGENT decisions,
verification/fixture evidence, scale/security/test-honesty findings, user demo and risks.
For unattended work list consequential decisions made without the user separately.
No arbitrary numeric risk score or CI-enforced percentage is required.

Check CI at the actual PR head and read conversation, reviews and inline review comments;
fix relevant failures and findings until green or a concrete external blocker. Avoid busy
polling. Do not turn an action-required/queued/absent check into a pass. The local review
report is not permission to post comments or merge. Leave the PR unmerged unless the
user authorizes this delivery's merge. Report the PR URL, what can be tried, decisions,
check results and material limitations.

## Resume and automation limits

On resume read the artifacts and Git/PR state, reuse existing evidence at its recorded
revision, and rerun only checks invalidated by new changes, base movement or uncertainty.
Do not repeat reconnaissance without a reason. Design/brief edits do not automatically
launch an agent. The validator checks artifacts, mirrors, declared verification and
prompt completeness; it cannot prove command execution, meaningful assertions, genuine
independence or full workflow compliance. Those require execution evidence and review.
