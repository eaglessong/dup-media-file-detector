# Local state and evidence

State lives in ignored `.agent-local/ship-it/<owner-repo>/pr-N/state.json`. It is one
coordinator's resumable log, not a signed authorization token or proof of GitHub state.
Do not store raw private comment bodies, credentials or sensitive paths; keep IDs,
version digests, commit/run URLs, concise dispositions and verification receipts.

The standard-library helper operates only on the explicit local state path. It never
runs gh/Git/tests, posts, pushes, schedules or merges. Read the resulting JSON/status
after every command; a nonzero exit means no successful progress write. Lock contention
exits 3; invalid input/state or an I/O failure exits 1. It uses a nonblocking POSIX lock
and atomic replacement. Do not remove another writer's lock or run competing coordinators.

```sh
python3 scripts/ship_it.py init --state .agent-local/ship-it/owner-repo/pr-12/state.json   --repo owner/repo --pr 12 --head REAL_HEAD_SHA --base REAL_BASE_SHA --max-rounds 20 --no-merge
python3 scripts/ship_it.py round --state PATH
python3 scripts/ship_it.py observe --state PATH --input observation.json
python3 scripts/ship_it.py verify --state PATH --input verification.json
python3 scripts/ship_it.py note --state PATH --input triage-or-history-event.json
python3 scripts/ship_it.py failure --state PATH --signature SAFE_NORMALIZED_CAUSE
python3 scripts/ship_it.py finish --state PATH --status merge_ready
python3 scripts/ship_it.py read --state PATH
```

Replace SHA/path/number examples with real values using safe argv calls. Default init
is merge-enabled bookkeeping (`no_merge=false`), but actual current user merge authority
is always required. --no-merge is sticky across init/resume; omitting it cannot clear it.
Existing identity, counters, receipts and history survive init. A smaller requested
round cap can tighten a run, not reset/increase it. For a later explicitly authorized
new run, `init --new-run` archives old state with a generated name and initializes a
new one. Do not use this to evade retry/round bounds or the user's no-merge instruction.

Observation JSON: `{"head":"<40 or 64 hex>","base":"<40 or 64 hex>",
"feedback_digest":"<nonempty safe digest>"}`. Head/base changes clear verified refs;
feedback-version changes are recorded for re-triage. Verification JSON has the same
head/base, `"source":"execution"`, and a nonempty `commands` list of `{"command":"...","exit_code":0}`.
Simulated fixture results must use `note` with `source: simulation`; `verify` rejects
simulation provenance. The source field is still a caller assertion. Only matching current refs and all-zero recorded exits can set verified refs. These
are caller assertions, not proof commands ran; actual CI, feedback and merge gates are
still the agent's job. A successful helper check does not imply real-world readiness.

`note` appends a JSON object to history (e.g. item identity/version, disposition,
reason, pushed fix SHA and reply ID). It cannot replace previous history or change mode.
`failure` increments a normalized cause count; three failures block. `round` cannot
exceed the saved cap or advance a terminal run. `finish` accepts waiting, blocked,
merge_ready, merged or closed. merge_ready/merged require verified current head/base;
merged additionally requires --merge-commit and rejects a persisted --no-merge run.
Merged/closed/merge_ready are terminal; continue only under a new explicit request.
A blocked run preserves its evidence and bounds; a fresh run needs an actual new scope
or changed external condition and a fresh explicit user instruction. Resume terminal
blocked state with `init --new-run` only under that instruction; retain `--no-merge`
unless the user explicitly changes merge authority. Never reset automatically.

Do not treat records of --no-merge preparation as permission to merge later. Immediately
before any real final action repeat the live gates in the playbook, regardless of state.
Keep the state/report for audit and next-session handoff; report rather than silently
claiming the process continues after the current task ends.
