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


## STAMP — delivered, unmerged

PR: https://github.com/eaglessong/dup-media-file-detector/pull/8
Reviewed/tested implementation43b7ae6a5eb9524e9af2068763eab73ab2d2b7f9;
base cac461f8f362ab4817533b5bc38447bb2be9fc1f.
All five checks SUCCESS at that head: Linux application3.11/3.13,
macOS3.11/3.13 and framework.
Application run https://github.com/eaglessong/dup-media-file-detector/actions/runs/44248249425
Framework run https://github.com/eaglessong/dup-media-file-detector/actions/runs/44248249440
Downloaded CI log confirms Linux privileged31 integration+8 E2E per Python;
macOS mandatory native31 integration, and25 E2E total (18pass,7Linux-only skips)
per Python, including all7 new macOS E2E. Required cross-volume/nested-mount cases
execute after APFS image attachment, with no native-case skip in that stage.
Earlier broad integration invocation intentionally skips the2 image-required cases,
which are then run successfully by the mandatory image stage.
PR conversation/reviews/inline all empty after verification. Final artifact-only commit
will be checked again at its own head; source evidence above remains pinned honestly.
Synthetic image successfully detached and removed; no user originals operated on.

Try normal-user macOS APFS dry-run from repository:
`python3 -m dup_media --move-duplicates SOURCE --destination DEST --dry-run`.
Header identifies macos-data-only; resource forks block, other metadata is not copied.
Execution additionally needs a new external --journal and --exclusive-access.
No merge authorized/performed. complete means review-ready, not merged.
