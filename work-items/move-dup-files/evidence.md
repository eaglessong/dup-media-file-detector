# Move duplicate files — design evidence

## Authority and snapshot — 2026-11-18

USER requested forge creation of `move-dup-files` and its related design, explicitly
“Do not implement.” Scope is artifacts only: no application/test edits, media moves,
PR creation, remote posting or merge. Baseline HEAD/main/origin-main at exploration:
`cac461f` (patrol workflow merge); initial working tree clean. Created branch
`codex/move-dup-files` and used `python3 scripts/forge.py new-feature move-dup-files`
(exit0). Four feature scaffolds created; ADR-003 added separately.

Read AGENTS, PRODUCT, WORKFLOW, CONTRIBUTING, forge skill, prompt/evidence contract,
knowledge map, test-data/decision/capture protocols and accepted first-scan/summary ADRs.
FULL planning track: this introduces explicit mutation, path handling, transfer/recovery,
metadata and a CLI contract. Execution is single-agent multi-pass reconnaissance, not
independent review. Rendered all five PROSPECT prompts with exact context via
`python3 scripts/forge.py render-prompt ROLE --context .agent-local/move-dup-files/prospect-context.json`
(all exit0); prompts/context saved ignored locally. Applied their separate instruments:

| Instrument | Receipt read this run | Finding / consequence |
| --- | --- | --- |
| Archaeologist | git log -4 --oneline; ADR-001/002; docs/design/first-scan.md | Existing application commits add inventory and summary, not relocation. ADR-001 explicitly requires fresh validation before moves. Preserve existing read-only defaults. No remote issue/history completeness claim. |
| Architecture Mapper | dup_media/__main__.py:16–32; scan.py:61–73,153–182,216–289 | CLI runs scan then streams JSON; SQLite has signatures but output lacks enough execution state. Existing source access is read-only. Plan directly from fresh validated disk index, not saved JSON. New journal/executor needed later. |
| Scale Analyst | PRODUCT workload prose; scan.py:189–255; CONTRIBUTING | Hundreds of GB/no scan-time limit is owner intent, not measured throughput. Current matching does streaming reads/disk index. Copy/verify adds substantial I/O and total destination capacity; file count/NAS measurements unavailable. Plan bounded synthetic measurement and real cross-device evidence. |
| Test Landscape | tests/integration/test_scan.py; summary integration assertions; tests/e2e/test_cli.py; application workflow; fixtures provenance | Existing real-tree tests cover aliases/changes/permissions/hardlinks; subprocess tests cover JSON and SIGINT. No relocation coverage. Need shared transfer/keeper/conflict/journal fixtures and real two-filesystem E2E; existing CI does not provision this evidence explicitly. |
| Premise Challenger | request vs CLI/scan; ADR-001 safety; source signatures and final validation | Goal is absent and valid, but scan output is not deletion authority. Same-inode paths, metadata loss, overwrite, cross-volume crash windows and concurrent namespace mutation need explicit contracts. No proposal to use hash-only proof or claim reclaimable bytes. |

## SURVEY

After exploration, asked keeper policy, cross-volume support and fresh scan versus saved
inventory. USER selected (verbatim):

- “Keep the first root-relative path in deterministic alphabetical order (Recommended)”
- “Yes—copy, verify, then remove the source; retain the source on failure (Recommended)”
- “Scan afresh, then plan and move; dry-run shows the plan (Recommended)”

Follow-up material ambiguity: cross-volume metadata preservation. USER selected:

- “Preserve bytes, permissions and modification time; reject files with metadata the tool cannot preserve (Recommended)”

No expired/default option was treated as a response. Recorded choices and separately
attributed AGENT defaults in ADR-003. Keeper ordering details, strict overlap/no-overwrite,
external journal, stop-on-failure, explicit CLI mode and exclusive access are AGENT choices.

## SMELT and fixture gate

Authored docs/design/move-dup-files.md before any implementation. R1–R9 specify paths,
copy verification, early root rejection, dry-run, fresh proof, conflicts, strict metadata,
journal/recovery, legacy compatibility and bounded resources. CLI examples explicitly
future-only. No application behavior is claimed shipped.

Test-data feasibility verdict ADEQUATE for design only: original synthetic byte trees,
empty files, links, POSIX modes, Unicode/case collisions, controlled mutations and
subprocess checkpoints can express expected behavior. Real cross-filesystem and metadata
capability validation needs a non-root Linux CI setup with two writable filesystems.
No actual transfer fixture/probe or test execution occurred. Unsupported adapters must
fail closed; no NAS certification or mocked-cross-device substitution is accepted.

Capture/storage probe trigger identified for no-replace publication, fsync/durability,
metadata detection/preservation and target filesystem support. The design records early
disposable probes as implementation prerequisites. No service/media capture needed;
no external storage inspected, private media read, or platform result invented.

## Design consistency review

Single-agent design review, not implementation ASSAY or independent code review:

- Separated scan-only authority from explicit future relocation; request remains design-only.
- Changed proposed raw rename to staged copy plus atomic no-replace publication candidate;
  ordinary rename/replace cannot silently overwrite a racing destination.
- Did not claim descriptor checks eliminate check/unlink races: exclusive trees required,
  arbitrary concurrent writers/mount actors explicitly unsupported.
- Strict metadata choice requires capability adapter and fail-closed behavior, not a
  copystat-only promise. New dependency/platform feasibility returns to SMELT if needed.
- Distinguished detected preflight blockers (zero mutation) from late execution failures
  (possibly completed moves or redundant copies); no batch atomicity/automatic rollback.
- Explicitly accounted for hardlink ctime and directory changes made by the operation.
- Dry-run creates no destination/journal; existing external scratch/read-atime caveat kept.
- Defined future integration/E2E acceptance, recovery/pipe/signal cases and exact fixture
  outcomes. These remain plans, not passing tests.

## Design delivery

Design delivered with brief, ADR-003, phase/status and this evidence. Stop here. No
implementation, new tests, runtime checks, PR or moves. Future implementation must
reconfirm metadata/publication/platform probes, add real integration/CLI tests, perform
forge ASSAY and deliver verified CI under new authority.

Document/structure verification: `python3 scripts/forge.py check` exit0; `git diff
--check` exit0; explicit Python whitespace/link validation of all five new artifacts
passed (untracked files are not covered by ordinary diff). `git diff --exit-code HEAD
-- dup_media tests .github/workflows scripts` exit0 confirms no application/test/CI/tool
changes. HEAD and merge-base with origin/main were resolved and identical. No application
commands or tests ran; structural validity is not proof of move behavior.

## Implementation resume — 2026-11-18

USER `/forge implement move-dup-files` authorizes implementation/tests/PR, not merging
or operating on a real library. Base remains cac461f8f362ab4817533b5bc38447bb2be9fc1f;
prior untracked design artifacts preserved. Re-read applicable rules/design and refreshed
five bound PROSPECT prompts; unchanged source reconnaissance reused. A delegated
architecture/premise reader identified privileged xattr visibility and creation-time
constraints, then USER explicitly approved required Linux metadata capabilities and
new inode/creation time. ADR003/design updated before code. The other three reconnaissance
instruments reuse recorded source/history/tests because base unchanged.

Initial adapter is Linux ext4/tmpfs only, root with required effective capabilities.
No claim that listxattr under ordinary user proves hidden metadata absent. Preserve
uid/gid/mode/mtime/user.*; reject other namespaces and flags. Unsupported platforms
fail closed; ordinary scanner untouched. Docker daemon unavailable locally; GitHub
Linux CI supplies actual early storage/metadata/cross-device probes. Candidate mechanism
is provisional until those probes pass. This is not a Linux/NAS success claim.

FORGE: added explicit relocation mode, bounded SQLite plan, pinned roots/directories,
copy/exact-verify/no-replace publication, external durable journal, and per-path source
removal with controlled alias-ctime refresh. Added privileged Linux integration and
actual-module cross-device E2E fixtures; CI requires capabilities instead of skipping.
Local macOS compile/contract checks pass; new root/mode rejection tests pass. Privileged
move tests explicitly skip locally (12 integration,3 E2E at this checkpoint). Preparing
an incomplete draft PR to obtain required Linux filesystem evidence; no completion claim.

## TEMPER / real Linux capability evidence

Draft PR: https://github.com/eaglessong/dup-media-file-detector/pull/8.
Initial CI44244344141 at8246fc3 failed one privileged diagnostic assertion: Scan.source
wrapped MoveError as SourceFailure, hiding its specific metadata code. Fixed by using
a relocation checked-source context preserving error codes and accounting only for
controlled ctime updates. CI44244518206 passed both Linux versions atc43105d.

Added mount aliases, last-moment identity/byte checks, actual ACL/flags, cross-device
hardlinks and deterministic signal boundary probes. CI44244662426 at5dfb8fc passed all
21 privileged integration tests but failed the dropped-user CLI fixture because runner
home was not importable by that user. Corrected the fixture to provide a readable copy
of the shipped package in a disposable directory; did not weaken expected refusal.

CI44244874498 at1bc5289 passed Linux Python3.11 and3.13:
-2 application contract tests each; unprivileged integration46 discovered,25 passed,
 21 privileged cases explicitly skipped there; privileged rerun22/22 passes (including
 root-safety test). No privileged test skipped with REQUIRE_MOVE_TESTS=1.
-Ordinary E2E16 discovered,11 passed/5 privileged skips; privileged E2E6/6 passes,
 including real distinct-device ext4↔tmpfs transfer, dropped privileges, SIGINT and
 SIGKILL receipts. Legacy permission/filename tests ran as the normal runner user.
-Real ACL/trusted-xattr/NODUMP rejection, no-replace conflicts, hardlink ctime,
 directory replacement, bind mount/nested mount rejection and user-xattr/mode/mtime
 preservation passed. File/directory fsync succeeds in ordinary transfer paths.

Bounded Python3.13 Ubuntu measurement from same CI, using scripts.probe_move:
10,00016-byte selected files/160,000source bytes/5,000groups: dry-run2.773seconds,
peak RSS32,576KiB, SQLite index3,633,152bytes. Separate16,777,216-byte relocation:
0.152seconds, process peak RSS37,256KiB. Includes full fresh scan/copy verification;
synthetic runner/cache result, not NAS/production throughput or asymptotic proof.
Full local log retained ignored in .agent-local/move-dup-files/ci-44244874498.log.

Local non-root macOS Python3.13.16: framework29 tests pass; compileall/CLI help and
2 contracts pass; integration and CLI suites pass applicable tests with Linux privilege
cases and one filename fixture explicitly skipped. Local skips do not claim transfer
success; Linux hosted runs supply that evidence. No private roots were scanned.

Additional source review found and fixed final-boundary checks: after the last callback,
reopen pinned roots/parents, reprove both source signatures and destination metadata/
bytes before unlink. The added same-size source/destination mutation regression passes
in CI44244874498. Cooperative source/destination directory locks and explicit exclusive
access acknowledgement supplement, but do not claim to eliminate arbitrary writer races.
A final compatibility guard rejects32-bit Linux and missing libc statx rather than
leaking AttributeError; source semantics and Linux test paths otherwise unchanged.

Entering Full ASSAY: code-review five roles plus implementation challenger, scale,
diagnostics/security and test-realism instruments. Coordinator owns all edits/tests;
reviewers read only, do not execute candidate code or claim human independence.

## ASSAY findings and fixes

Full code-review used architecture/operational roles and implementation+scale audits
in one agent, deep-read/repository rules+diagnostics in a second, test-impact/realism in
a third, then a separate fourth Devil's Advocate. All read-only, no reviewer code/test
execution or GitHub publication. Same model agents; no human independence claimed.

| Finding | Disposition |
| --- | --- |
| F1 P1 existing DEST independently flocked twice | FIXED identity-based lock reuse; new integration/CLI existing-root cases pass; early-journal injector asserts reached |
| F2 P2 dry-run scratch could enter DEST, including tempfile probe/static bind aliases | FIXED read-only explicit scratch selection, canonical physical mount containment for both trees, SQLite native spill directory pinned/verified externally; names/timestamp regressions |
| T1 P2 post-unlink recovery coverage absent | FIXED real SIGKILL after physical unlink and after receipt, failing source_removed journal commit, partial multi-victim failure/count checks |
| T2 P3 metadata injection mislabeled copy failure | FIXED narrower name and separate10-byte partial staging-copy write failure with observed injector/error receipt |
| tmpfs metadata flags/volatility lead | ABSORBED by ext4-only support and real second-ext4 CI, explicit tmpfs rejection |
| Missing journal identities/digest/error receipts | ABSORBED into durable schema/error receipts |
| New challenge: independent native SQLite spills and ext4 project IDs | FIXED verified temp_store_directory pin/restoration and FSGETXATTR policy with real sort/nonmutation and project-ID fixtures |

A new regression initially failed due to calling Mock.assert_called_once on the
replacement function (CI44245540142/44245603409); corrected side_effect wrapper
without weakening expected behavior. CI44245701443 at33343f2 passed after that fix.
Canonical bind scratch alias and SQLite/project probes added afterward; full final
source CI44246046573 at219b29c92e68548cd7c4b3484691d71c5e3e7c86 passes both Linux versions.

Final test audit:39 methods read,31 integration+8 E2E,39 HONEST/0 WEAK/0 LYING/0 DEAD.
Initial audit28, then36, then39 as safety regressions added; no fabricated denominator.
Detailed ignored report .agent-local/reviews/move-test-audit.md. Synthesis:
.agent-local/reviews/move-dup-files-review-20261118.md. No unresolved blocker/advisory.
Final challenge source verdict covers219b29c; author overlap disclosed.

## Final TEMPER / evidence at219b29c

Linux Python3.11 and3.13 CI44246046573 (both SUCCESS):
-2 application contracts; normal filesystem55 discovered/26 pass/29 capability skips,
 followed by mandatory privileged relocation31/31 pass without skips.
-Normal actual-module E2E18 discovered/11 pass/7 capability skips, followed by mandatory
 privileged relocation8/8 pass without skips. Linux filename and non-root mode cases
 remain covered by the normal-user suite.
-Actual distinct-device ext4↔ext4 CLI transfer; real bind/nested mount rejection,
 ACL/trusted attrs/NODUMP/project-ID rejection, owner/mode/mtime/user.* preservation,
 crash action/receipt gaps, no-clobber/copy failure/journal failure/partial batch cases.
-Framework CI44246046704 SUCCESS. Runtime32-bit/missingstatx unsupported guard remains
 explicit; no additional supported platform is claimed.

Final Python3.13 Ubuntu bounded measurement at219b29c:10,000 files of16 bytes,
5,000pairs,160,000 source bytes:1.620seconds, peak RSS32,952KiB, SQLite3,633,152bytes.
Separate16-MiB move:0.314seconds, process peak RSS37,556KiB. Real generated bytes and
fresh scan; these are synthetic CI measurements, not Synology throughput or a speed
threshold. No actual physical-disk spill, disk-full or power-loss result claimed.
CI log .agent-local/move-dup-files/ci-44246046573.log retained locally.

Final local macOS checks run individually and recorded exit0: forge check,29 discovered
framework/application tests, compileall, module help,2contract tests, full integration
and E2E discovery with explicit platform/capability skips. Logs and exact commands are
.agent-local/move-dup-files/final-local-checks.json and final-local-check-0..6.log.
No test used personal media. No source-library mutation occurred outside disposable tests.

## STAMP / delivery

PR#8: https://github.com/eaglessong/dup-media-file-detector/pull/8.
Complete means owner-review-ready, not merged. Actual CLI/demonstration contract is
exercised in shared integration/E2E fixtures: equal a.jpg+nested/b.jpg leave a.jpg;
only nested/b.jpg relocates with the same relative name; unique media unchanged.
Dry-run reports planned1/moved0 and creates no target/journal. No private-library demo.

Final artifact update changes no reviewed application/test/CI/probe source after219b29c.
Final structural and whitespace checks cover metadata; final commit CI is checked
before handoff and PR is marked ready only after successful current-head checks.
Fresh PR conversation, reviews and inline comments are inspected before delivery;
findings/failures are fixed, not waived. Full source/CI evidence remains as above.
No merge, release, actual-library operation, scheduler or background watcher authorized.

Retained limitations: Linux64 ext4 only with explicit capabilities, exclusive source/
destination/ancestor namespaces, manual crash recovery, no actual hardware power-loss/
disk-full certification, no NAS/btrfs/macOS relocation support, logical not reclaimable
byte counts, unsupported metadata refusal. Status mode independent means separate-agent
review only, not human-independent approval. Feature commits and evidence preserved on
codex/move-dup-files; final handoff reports actual PR/head/check state.


### macOS extension
User subsequently authorized macOS support with metadata relaxation and resource-fork
rejection. See work-items/macos-relocation/evidence.md and ADR-004 for this separate
work item extending PR8. Earlier Linux evidence remains historical at its cited revision.
