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
