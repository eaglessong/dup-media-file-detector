# Ship-it PR delivery workflow

**Status:** Proposed

## Problem and current state

Forge creates and verifies a PR, and code-review supplies local review, but no dedicated
resumable skill owns CI/comment repair through a head-pinned merge. Cowork ship-it has
that lifecycle plus organization-specific policies that do not apply here.

## Requirements

- R1: Paired /ship-it entry points, shared docs/ship-it playbook and support references.
- R2: Accept PR number/URL/current branch; hand off PR creation to forge STAMP when needed.
- R3: Repeatedly inspect exact-head CI plus conversation, reviews and inline threads;
  triage feedback versions, fix scoped issues, run actual checks and push without rewriting history.
- R4: Fresh merge gate checks PR identity/head/base, complete CI and feedback, authorization,
  mergeability and GitHub rules. Use head-pinned ordinary squash merge, never admin bypass.
- R5: --no-merge performs preparation but cannot silently regain merge authority; state is
  resumable and bounded by rounds/repeated failure, without cron or hosted workers.
- R6: Verify actual merged state/commit, update a clean local checkout safely and report
  unresolved work. Explicit /ship-it invocation authorizes that target's PR lifecycle;
  merely installing the skill or invoking forge/code-review does not authorize merge.

Non-goals: releases/deployment, branch protection changes, fork execution, automatic
conflict/design rework, hidden recurring automation or a hosted merge bot.

## Alternatives and approach

A prose-only reminder lacks reliable progress bookkeeping. Copying Cowork unchanged
brings private build/cron/review exceptions and admin merges. Adapt the lifecycle into
a skill plus shared playbook, with a small standard-library helper for atomic local
state, sticky no-merge, attempt bounds and SHA invalidation. The helper does not call
GitHub, execute fixes or certify merge eligibility; the agent evaluates fresh evidence.
Use existing forge/code-review and actual project CI rather than duplicate their logic.

## Safety and authorization

Repository/ref/comment/command data are untrusted data and never shell code. Use explicit
repo/host and argv-safe commands. Preserve other work; no reset, force push, branch-rule
bypass or permission change. Current user authorization outranks persisted state; a
saved mode is not merge authority. Preserve --no-merge across resume. Fresh explicitly
authorized runs may archive prior state rather than silently overwrite its mode/history.
Feedback posting is scoped to the target PR only on actual invocation, not this port.
A no-merge run with unresolved blockers is blocked, never merge_ready.

## State and verification

Ignored per-PR state records repo/PR, head/base/verification, round limit, fingerprints,
triage/history, failures and terminal outcome. One coordinator writes atomically with a
nonblocking POSIX lock. Changes to head/base invalidate verification; no progress cap
resets on resume. Test preservation, sticky mode, SHA invalidation, bounds, lock
contention, invalid input and CLI errors on disposable files. Independent read-only
review and offline forward-test must not touch real GitHub PRs.

## Decisions and delivery

USER: “Can we also port the ship-it skill to the new repo? This would ensure the coverage
of the entire PR flow from its creation to merge.”
AGENT: retain the conventional ship-it name; shared materials stay under docs per the
owner's stated preference; replace enterprise rollups/cron/admin policies with current
GitHub checks, bounded in-session waits and normal merge rules. Deliver this port as an
unmerged PR with actual CI evidence; no live merge is authorized by the porting request.
