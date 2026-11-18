# Evidence — macOS relocation

Track FULL: platform and destructive filesystem boundary. PROSPECT five bound instruments: history/architecture/premise by macos_scout; scale/tests by macos_test_scout. No reviewer executed candidate code. Reports identify Linux-only metadata/tests, physical firmlink paths, procfs journal incompatibility, RSS unit caveat.

SURVEY: USER explicitly rejects resource forks and allows other metadata loss. SMELT: design and superseding ADR-004 authored before application edits. Native coordinator probes: macOS27.2.1 arm64/APFS; directory fsync, file F_FULLFSYNC51, descriptor link publication succeed. Physical path command102 returns Data-volume spelling; command50 returns logical path. SQLite /dev/fd/dir/child fails, motivating pinned ordinary path. os.setxattr unavailable, motivating native descriptor APIs.

No application verification claimed yet. Cross-volume image execution pending. All fixtures synthetic/disposable. Existing PR8 will receive this coherent extension; no merge authorized.

## TEMPER — native macOS

Environment macOS27.2.1 arm64, Python3.13.16, APFS, normal user. Disposable128MiB
APFS sparse image attached under temporary storage; real cross-device assertions pass.
Initial sandbox hdiutil attempt failed Device not configured; approved retry succeeded.
No personal media accessed. Commands/receipts in ignored .agent-local/macos-relocation/:

- `python3 scripts/forge.py check`: passed (structural, not application proof).
- `python3 -m unittest discover -s tests -v`:29 passed, including2 application contracts.
- `python3 -m compileall -q dup_media` and `python3 -m dup_media --help`: passed.
- Full native integration initially81 tests:51 passed,30 explicit Linux/encoding skips.
- Full entry-point E2E25 tests:18 passed,7 Linux-only skips.
- Final native dedicated integration31 tests and E2E7 tests use
  REQUIRE_MAC_MOVE_TESTS=1 and MOVE_CROSS_ROOT pointing to the disposable APFS image;
  native-integration.log/native-e2e.log retain detailed results. No native-case skips.
- `python3 -m scripts.probe_move`: original synthetic10,000×16-byte fixture,5,000 pairs,
  dry-run5.326s, index3,506,176bytes, peak34,752KiB;16MiB relocation0.268s,
  process peak39,280KiB. Darwin RSS normalized from bytes. Not NAS/hardware throughput.

## ASSAY — completed

Separate architecture/deep-read/scale reviewer found no blocking runtime issue.
Separate test-impact/rules/operations reviewer requested a real subordinate mount test;
added using mounted APFS fixture. Added native metadata-absence assertion, late destination
fork and flagged-file cases. Fixed Linux scope in README, stale fixture prose and test
name. Final separate Devil's Advocate is pending. No human-independent claim.
Linux/macOS CI pending against new PR head; existing prior Linux CI is historical only.


Final separate Devil's Advocate found no blockers; advisory post-publication fullsync
failure gap was closed with a real copied/published file plus second-call-only sync
failure injection: source and copy survive, moved0 and staged_verified receipt. Final
native integration31/31 pass (4.810s), E2E7/7 pass (2.423s), no native-case skips.
Delegated test audit37 methods all HONEST; coordinator separately audited added fault
method,38 total. Reviewer-authored report .agent-local/reviews/macos-test-audit-20261118.md;
synthesis .agent-local/reviews/macos-relocation-20261118.md. Separate agents, no human
independence claim. Blockers resolved; STAMP waits for final CI.

PR8 feedback read at928dac5: conversation/reviews/inline all empty; CI running.
