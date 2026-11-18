---
name: ship-it
description: Shepherd a GitHub PR through feedback triage, CI repair, verification and an authorized head-pinned merge. Use for ship it, land a PR, or prepare it with --no-merge. Not a release/deployment workflow or permission to bypass branch rules.
---

# Ship It

Read `AGENTS.md`, the [iteration playbook](../../../docs/ship-it/iteration-playbook.md)
and its [state protocol](../../../docs/ship-it/state-and-evidence.md). Repo-root paths
refer to the target checkout. This adapts Cowork ship-it without internal services,
admin merges, headless cron workers or organization-specific reviewer exceptions.

## Invocation and authority

`/ship-it [PR number or URL] [--max-rounds N] [--no-merge]`

With no target, resolve the current branch's PR. If none exists, follow forge STAMP to
review/verify the actual branch and create the PR, then continue. Do not select among
multiple PRs or use an unrelated dirty checkout silently. The default round limit is 20;
stop on the same failed repair three times, a conflict, design/authority blocker, or
exhausted rounds. Do not create a scheduled automation to monitor this finite task.

An explicit user invocation to ship/land the identified PR authorizes scoped fixes,
verification, commits/pushes, necessary replies on that PR and ordinary squash merge
once every gate passes. `--no-merge` permits preparation/replies/pushes but withholds
merge; unresolved blockers still block, rather than producing a false merge_ready.
A request only to review, implement, port/install this skill, or prepare a PR does not
authorize merging. Forge never silently escalates itself to a merge-enabled ship-it run.
No release/deployment, branch-rule change, force push, unrelated issue filing or private
media operation is authorized by this skill.

Respect persisted --no-merge and the current user's scope; state is not authority.
Reentering a saved no-merge run without the flag does not enable merging. A later
explicit user instruction to merge can start a new authorized run, archiving the prior
state rather than silently clearing its mode. Do not ask for routine permission again
when current user intent already authorizes the target action.

## Execution

Use one coordinating writer and ignored per-PR state under `.agent-local/ship-it/`.
The state helper performs atomic, locked local bookkeeping; it never queries GitHub,
runs tests, certifies readiness or performs a merge. Follow the playbook for actual
fresh evidence, triage, repair, bounded waits and final gates. Use code_review for
review and forge for design-level changes; neither recursively launches ship-it.

Keep working in the current task through checks/repairs until merged, merge_ready
(--no-merge), already merged/closed, or a concrete blocker. If tool limits prevent
continued waiting, save accurate pending state and report the limitation; never claim
background monitoring was armed. Delegation is optional when permitted; do not pin
models or invent independent reviewers. Report meaningful changes without noisy polls.

Before merging reread target/head/base, complete checks, feedback and holds. New or
changed evidence invalidates the prior decision. Never use --admin, pending-check
waivers or remembered green results. Pin the merge to the verified head SHA and let
GitHub enforce protection. Verify actual MERGED state and merge commit afterward;
update local main only when it is safe to fast-forward a clean checkout. Preserve state
and report paths, failures, dispositions and unresolved limitations for resumption.
