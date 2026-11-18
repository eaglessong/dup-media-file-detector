# Ship-it port — execution evidence

## PROSPECT and design

FULL: new agent/merge instructions and persistent helper. Read Cowork ship-it, its
iteration-playbook phases/gates and pending-merge configuration, then mapped applicable
lifecycle to the current forge/code_review, Python/POSIX checks and owner authority.
See docs/design/ship-it-port.md and docs/ship-it/PORTING.md. Internal build/cron/admin
policies are replaced, not imported. No application behavior changes.

Fixture verdict ADEQUATE: disposable JSON state, subprocess CLI calls, simulated I/O
failure/lock contention, and an isolated offline PR snapshot. No personal media or
service credentials are needed. Design was recorded before target implementation.

## Implementation and TEMPER

Paired ship-it entry points, shared playbook/state protocol/adaptation map, forge/agent/
README integration and missing-resource/mirror checks. The local helper never executes
remote actions: it records sticky mode, attempts, refs, evidence/history and outcome.

## TEMPER and ASSAY results

- Framework check passed; unittest discovery passed 27 tests on the local Python runtime.
- Both mirrored ship-it entrypoints passed skill-creator quick_validate.
- Independent read-only code review found one malformed-state advisory: missing nullable
  keys could cause a traceback. Fixed by requiring keys; CLI regression cases delete
  each key across active/final statuses and confirm controlled errors and preserved bytes.
- Independent offline forward evaluation of `/ship-it 12 --no-merge` correctly blocked
  on an edited owner comment and human changes-requested hold despite fixture-green CI.
  It preserved no-merge, did not ignore owner feedback, and made no remote actions.
- Evaluation improvements applied: discover/verify repository identity; explicit terminal
  resumption instructions; structured execution provenance rejects simulated verification.
  Receipts remain caller assertions, not proof of actual execution.
- Offline fixture omitted full diff/workflow/Actions metadata. It tests blocked triage,
  not live GitHub CI, comment posting or merge. No real PR was merged in evaluation.
- Application behavior unchanged; hosted application integration/E2E remains CI's task.
  Fixture-supplied CI is never counted as an actual live result.

## STAMP

Port ready for PR delivery. Hosted CI will be checked against the pushed commit.
 The porting request does not authorize
invoking ship-it against a real PR, posting review replies or merging.
