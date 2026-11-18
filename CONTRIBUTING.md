# Contributing through artifacts

Explain the intended behavior in `docs/PRODUCT.md`, a feature brief, or an issue.
Follow `docs/WORKFLOW.md`; maintain brief/design/status/evidence and attributed ADRs.
Use `codex/<slug>` branches, Conventional Commits, and the PR template. Never merge
without owner authority or invent author identity.

Python 3.11+ standard library with SQLite and POSIX descriptor-relative filesystem APIs
is the application/runtime stack. Run from the repository; no dependencies to install
and no build/package generation step. Syntax compilation and CLI contract tests are
the applicable application checks; no external formatter/linter/type checker configured.

```sh
# Framework structure and framework tests:
python3 scripts/forge.py check
python3 -m unittest discover -s tests -v
# Application syntax and CLI contract:
python3 -m compileall -q dup_media
python3 -m dup_media --help
python3 -m unittest discover -s tests -p test_application.py -v
# Real filesystem integration:
python3 -m unittest discover -s tests/integration -v
# Actual shipped CLI in subprocesses:
python3 -m unittest discover -s tests/e2e -v
```

Framework CI and application CI run separately; application CI covers Linux Python
3.11/3.13. Permission tests skip under root (which bypasses modes); local non-root runs
exercise actual permission failures. Cancellation uses sparse synthetic files. All
fixtures are disposable, never personal media. Keep private paths, credentials, and
copyrighted sample collections out of Git. A project license remains undecided.

Forge contributors: shared role prompts and protocols live in `docs/forge/`. See its
prompt contract for `scripts/forge.py render-prompt ROLE --context FILE.json`. Changes
must preserve declared input bindings, relative material links and paired skill entry
points. Run framework validation/unit tests and evaluate changed execution instructions
in a disposable scenario; structural checks alone do not prove agent behavior.

Ship-it contributors: shared playbook/state guidance lives in `docs/ship-it/` and its
local helper is `scripts/ship_it.py`. Framework test discovery runs the helper's tests.
Keep no-merge durable and never treat local state as remote merge authorization/proof.
Behavioral skill evaluation must use offline fixtures; do not merge a real PR merely
to test the port. No service credentials are needed for local framework tests.

Media-size-summary tests share synthetic recipes in `tests/summary_fixtures.py`.
Integration and CLI suites assert exact totals for unique/duplicate/hard-linked paths,
selection, empty trees, partial errors and large sparse logical lengths. The indexed
arithmetic case in `tests/test_application.py` verifies totals beyond signed 64-bit;
it is not a huge-filesystem test. Existing CI discovery runs these tests automatically.

Patrol contributors: docs/patrol/sweep.md defines publication/deduplication behavior.
Evaluate with offline PR snapshots; installing the skill does not authorize posting
live reviews. Keep both skill entrypoints mirrored and run framework checks/tests.

Relocation tests add privileged Linux metadata/namespace and real cross-device cases.
The application workflow runs ordinary suites as the runner user, then invokes only
relocation tests under sudo with `REQUIRE_MOVE_TESTS=1` (missing prerequisites fail,
never skip). ext4 scratch plus `/dev/shm` tmpfs must have distinct device IDs. Tests use
only new synthetic temporary trees; bind mounts are unmounted in finally blocks.
A Python3.13 CI step runs `sudo python3 -m scripts.probe_move` for bounded 10,000-file
planning and 16-MiB transfer measurements. macOS explicitly skips privileged tests;
this is not evidence that relocation works there. Do not remove strict metadata gates
to make an unsupported platform pass. ACL/trusted-xattr/flags probes are real fixtures.
