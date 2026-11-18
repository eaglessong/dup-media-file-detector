# Patrol port

Status: Proposed before implementation.

## Problem, discovery and decisions

Cowork patrol combines local aether-review with GitHub publication and head-based sweep
state. This project has mirrored code-review and ship-it skills, ignored .agent-local/,
and framework/application CI. Its review command is now `/code-review` (hyphen).
USER: port /patrol. AGENT: retain shared resources in docs/, use existing review engine,
and deliver an unmerged PR. No new runtime helper or dependency is needed for an
instruction workflow; use documented atomic JSON state updates and remote reconciliation.

## Requirements and non-goals

R1: Explicit PRs or a paginated open non-draft sweep, default updated within 24h, oldest
first. Explicit IDs force review, not duplicate publication. R2: Use code-review without
changing its read-only boundary, isolate other heads and pin base/head. R3: Publish
supported findings and CI/incomplete context, request changes only for blocking findings
on another author's PR; never approve/fix/merge. R4: Dry run writes only local reports,
not posts or sweep state. R5: Recover uncertain posts from remote markers; do not mark
failed/incomplete work reviewed. R6: Explain scope, errors, checks and skipped work.
No enterprise trailer, CI waiver, automatic schedule, branch mutation or media operation.

## Architecture, safety and operations

Mirrored skill entrypoints route to docs/patrol/sweep.md and existing code-review roles.
A single coordinator stores repo/operator-scoped ignored state. Review identity includes
head and base; remote markers bind both. A base change triggers review again. Review and
posting use GitHub metadata as data; no execution of candidate code, workflows or hooks.
Complete pagination and report coverage are prerequisites for any clean claim. A final
metadata refresh invalidates stale reports. Serialize invocations; atomic state replacement
prevents partial writes, remote recovery prevents duplicate posts after uncertain outcomes.
Continue other PRs after an individual failure and report a partial sweep honestly.

## Verification and acceptance

Synthetic offline scenarios: uncertain accepted post with stale local state; explicit
repeat; dry run on own PR; base movement and incomplete review. No live review posts
are authorized by installation. Framework tests check required materials/mirrors/links
by deleting or corrupting actual fixtures. Run skill frontmatter validation, framework
check and unit discovery. Independent read-only review/evaluation checks the workflow;
these are instruction tests, not application integration/E2E or GitHub publication tests.
Fixture verdict ADEQUATE for this scope; live API behavior remains untested by fixtures.

## Delivery and risks

Install via repository merge. Use `/patrol 12 --dry-run` then `/patrol 12` when publication
is wanted. Existing code-review/ship-it stay separate. Local state is bookkeeping,
not authority or proof of coverage. Multi-API races cannot be fully atomic; refresh and
bind review commit_id, report a later head movement. No material product questions.
