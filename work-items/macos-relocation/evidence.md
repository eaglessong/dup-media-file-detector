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


## PR8 follow-up — F1 reopened
Review https://github.com/eaglessong/dup-media-file-detector/pull/8#pullrequestreview-5951648652
at4318200 reports static permission omission. Current USER requests forge follow-up;
no merge authorized. Track FULL (filesystem safety); reuse full earlier scouts and add
five scoped instruments via two read-only scouts. Architecture/premise confirms Darwin
extended faccessat, test/history/scale maps real ACL/sticky/mode fixtures; O(plan×depth)
checks preserve disk-backed/bounded-memory design. No new consequential USER question.
Design/ADR-005 authored before fix. Native probes confirm source0555/deleteACL and
add_file ACL denial (errno13), while add_subdir can remain allowed. No application fix
verification yet. Privileged foreign-sticky fixture remains actual macOS CI requirement.


Follow-up TEMPER: native frameworkcheck passes;29 framework/application tests pass;
compile/help pass. Full integration89:56pass/33skips (29Linux,1encoding,2APFS-image,
1foreign-sticky); E2E28:19pass/9skips (7Linux,1image,1foreign-sticky). Logs retained in
.agent-local/pr8-permissions/. Initial new test run correctly exposed a test-contract
mistake: journal is not supplied in dry-run, so journal-only checks now apply only to
execution; initial optional sudo setup raised sandbox OSError, now explicitly skips
locally but fails required CI. No failure hidden as a pass. Existing modes/ACL cases,
whole-base snapshots and allowed ACL/sticky controls pass after correction. Native
foreign-owned sticky and cross-volume regression remain mandatory actual CI gates.


Follow-up CI at816e341: all five checks SUCCESS, application run
https://github.com/eaglessong/dup-media-file-detector/actions/runs/44251504515 and
framework run https://github.com/eaglessong/dup-media-file-detector/actions/runs/44251504474.
Downloaded logs confirm native34integration and10native E2E methods per Python3.11/3.13,
including required root-owned sticky fixture (privileged setup only, application under
ordinary user), real cross-volume and subordinate-mount cases. Full macOS E2E28 includes
7 explicit Linux-only skips;21pass, including all10native relocation cases. Linux
privileged31integration+8E2E still pass per version. No missing native-case prerequisite.

ASSAY: separate architecture/deep-read/implementation/scale and test-impact/rules/
operations/security agents report no blocking defect; all6 new methods HONEST.
Advisory fixture readability clarified by chmod0644 before root ownership; inheritedACL
README wording corrected. New fixtures are original bytes only. Final challenger completed with no blocking findings.
Arch stress hypothesis umask0100 causing later partial move was probed through shippedCLI:
exit2 before destination/journal creation, victim retained, because fresh SQLite scratch
is needed before any transfer. Specific hypothesis refuted, not blanket umask support.
Raw public Apple-source capture remains ignored; no external source/media copied into Git.


Follow-up ASSAY complete: separate final challenger confirms F1 resolved and no new
blocking defect; all6 added methods HONEST. Synthesis retained at
.agent-local/reviews/pr8-permission-followup-20261118.md. Current fixture refinement
(readable0644 before root ownership) and README clarity were reviewed; scoped6 local
methods rerun4pass/2explicit privileged-setup skips (4.790s). No app source changed
since the green816e341 run. Final artifact/test-only head will be CI-verified again.
Original F1 disposition FIXED, no outstanding review findings. Feedback refresh contains
only review5951648652, no inline/conversation comments. Feature status complete means
review-ready, not merged; no real media operation or merge performed.
