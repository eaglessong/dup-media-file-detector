# Cowork ship-it adaptation

The source skill/playbook shepherd an open enterprise PR using heartbeat-driven leads,
private pipeline rollups, state scripts and organization-specific review/merge policies.
This port keeps preflight, complete feedback/CI snapshots, triage-before-fix, verify-before-
push, bounded attempts, fresh final gates, head-pinned merge and post-merge confirmation.

Shared materials live under docs/ship-it; Codex/Claude skill entry points are mirrored.
Forge STAMP supplies creation/review when no PR exists. code_review stays local and
review-only; ship-it owns separately authorized replies, fixes, pushes and final merge.

Adaptations:
- Current GitHub Actions and actual branch rules replace fixed enterprise rollups.
- No admin merge, pending-check waiver, ignored bot hold, automatic review dismissal,
  synthetic status, private build machine, token service or hardcoded model.
- Comments/reviews/inline threads are paginated and versioned; only generated run
  markers are deduplicated, not every message by the operator's GitHub account.
- Bounded in-session waits replace cron/heartbeat jobs. State survives; monitoring does
  not continue after a task closes. Optional delegation never grants extra authority.
- A small atomic local helper replaces internal state tooling; it does not implement a
  trusted remote merge gate or execution engine. Explicit --no-merge survives resume.
- Narrow fixes may include necessary callers/tests outside the old diff. Conflicts,
  design rework, untrusted forks and missing authority stop the affected delivery.
- Merge outcomes are checked live; local update is clean fast-forward only, and state/
  unfinished work is preserved rather than force-removed.

Porting this skill does not invoke it against any real PR. Tests/evaluation use disposable
local state and offline scenarios; live PR merge remains a separate authorized operation.
