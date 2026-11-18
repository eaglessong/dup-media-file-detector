# Relocate exact duplicate media files

**Status:** Implemented, verified and agent-reviewed — PR #8 remains unmerged
**Date:** 2026-11-18
**Brief:** [move-dup-files](../../work-items/move-dup-files/brief.md)
**Decisions:** [ADR-003](../decisions/003-move-dup-files.md)

## Problem and current state

Baseline source receipts in this section refer to cac461f, before relocation changes.
Current execution evidence and test mapping are in the work-item evidence.

The existing CLI (`dup_media/__main__.py:16–32`) scans one root and emits a read-only
inventory. `Scan.run()` uses size/SHA candidates and byte comparison, then final file
and directory validation (`dup_media/scan.py:216–255`). The temporary SQLite index
stores paths, identities, sizes and timestamps (`:61–73`); serialized JSON exposes
paths/storage identity but lacks enough validation state for destructive reuse
(`:266–289`). No relocation implementation or move tests exist in inspected source.

This design adds an explicit relocation operation while retaining the current scanner
as read-only. The original delivery was design only. USER subsequently authorized implementation;
commands below now describe the explicit relocation mode. No real-library run or merge
is requested.

## Requirements and non-goals

- **R1 — Keeper:** For every freshly proved exact duplicate group, retain the first
  selected root-relative path in deterministic order; relocate every other path.
  Define order as SQLite BINARY order of UTF-8 relative paths, case-sensitive, without
  locale sorting, Unicode normalization, natural-number sorting or depth preference.
  Empty media and hardlinked paths participate. Unselected paths are outside the goal;
  one keeper means one selected pathname, not one inode or one copy across all storage.
- **R2 — Mapping:** `SOURCE/nested/name.jpg` maps to `DEST/nested/name.jpg`, without
  adding SOURCE's basename or flattening. Create missing destination directories only
  during execution. Preserve bytes, permission bits and modification time. USER also
  requires rejection if other attached metadata cannot be preserved.
- **R3 — Roots:** Reject DEST equal to or inside SOURCE before scanning, scratch/journal
  creation or destination creation. AGENT additionally rejects SOURCE inside DEST.
  Reject symlinks in either root/ancestors and `..` path components. Validate identities
  and containment, not raw string prefixes. Reject special-file roots and unsafe alias
  layouts; never let a symlink, bind mount or changed parent redirect writes.
- **R4 — Fresh proof:** Each relocation/dry-run scans afresh with current extension
  selection. Do not execute saved inventories/plans. Any scan error prevents all moves.
  Freeze a disk-backed plan only after validation; revalidate keeper and victim identity,
  metadata and exact bytes immediately before each operation.
- **R5 — Dry-run:** Use the same scan, keeper, mapping, metadata and conflict checks;
  report the planned actions and blockers without any persistent journal, directory,
  temp file or media mutation in either tree. Existing external scan scratch is allowed
  and cleaned. Read-atime effects remain possible. Dry-run is an observation, not a
  reservation of names, free space or future permissions.
- **R6 — No overwrite:** Never replace an existing destination entry of any kind,
  including identical files, dangling links and directories. A conflict found during
  global preflight aborts the whole operation before mutation. A late conflict stops
  further work with partial status. Never silently rename or skip it and claim success.
- **R7 — Transfer safety:** Support different source/destination filesystems. Copy to
  exclusively created staging storage, verify bytes and required metadata, synchronize
  durable destination data/name and operation state, then remove the matching source
  pathname. On copy/verification/publication failure leave the source in place. Keep
  the keeper; source removal is forbidden if its proof or identity has changed.
- **R8 — Partial recovery:** Durable per-operation states survive interruption. Stop at
  first execution error; completed moves remain completed, with no automatic rollback
  or continued blind retry. Never promise all-or-nothing batch atomicity. A source may
  remain alongside a complete destination after an ambiguous crash or unlink failure.
- **R9 — Compatibility/resources:** Existing `python3 -m dup_media ROOT` output,
  selection and exits remain unchanged. Plan/journal is disk-backed and streamed;
  byte copying/comparison uses bounded buffers and bounded descriptors. No uploads.

R1 keeper policy, R4 fresh scan, cross-volume copy/verify/remove, and strict metadata
preservation implement USER SURVEY choices. Additional conservative defaults and
interface/mechanism choices below are AGENT decisions, not claimed user preferences.

Non-goals: media decoding/similarity, deleting without relocation, reclaimable-space
claims, saved-plan execution, automatic resume/undo, pruning empty source directories,
interactive keeper selection, hardlink-topology preservation in DEST, concurrent writers,
snapshot isolation, hostile mount changes, releases or a new NAS support certification.

## Alternatives and recommendation

1. Execute old inventory: convenient, but stale byte proof and missing signatures need
   revalidation anyway; USER selected fresh scans instead.
2. Add optional move flags to ordinary scans: compact but mixes read-only and mutating
   contracts. Recommend a separately explicit invocation while keeping the legacy CLI.
3. Rename on one device, copy on another: fast locally but adds different crash,
   overwrite and metadata guarantees. Recommend one copy/verify/publish/remove protocol
   on both, accepting extra I/O and space for a smaller initial safety surface.
4. Plain `shutil.move`/rename-to-final: insufficient as the complete protocol; implicit
   overwrite/fallback behavior and weak recovery evidence fail R6–R8.
5. Continue around errors or rename colliding outputs: can produce a surprising partial
   source and changes mapping. Prefer global preflight then stop on execution failure.

## Architecture and interfaces

Relocation syntax:

```sh
python3 -m dup_media --move-duplicates SOURCE --destination DEST --dry-run
python3 -m dup_media --move-duplicates SOURCE --destination DEST --journal JOURNAL
# Existing --extensions jpg,png,... remains available in either mode.
```

`SOURCE` remains the positional root. `--move-duplicates` is a boolean mode, DEST is
required in that mode, `--dry-run` requires that mode, and actual execution requires
`--journal` naming a new external operation directory. Journal must be outside both
root trees; reject overlap/symlink/alias/occupied names. Dry-run forbids `--journal` so
it cannot create or truncate persistent artifacts. Ordinary scans reject move-only
options. Mode is explicit; no prompt or flag default authorizes writes.

Suggested modules: retain `Scan` as inventory/proof engine; add `dup_media/relocate.py`
for preflight/plan/execution and `dup_media/move_journal.py` for durable transitions.
Expose a bounded iterator over validated groups rather than reparse JSON. Extend
`__main__.py` routing deliberately and preserve scan-only regression contracts.

Execution stages:

1. Parse modes and validate SOURCE, DEST and JOURNAL without creating anything. Open
   ancestors descriptor-relatively without following links; for missing suffixes keep
   the nearest existing ancestor plus validated components. Walk ancestor identities to
   detect both directions of overlap, including filesystem aliases. A path such as
   `source-backup` is not a child of `source`. Reject nested mount/alias layouts that
   cannot be established safely; do not guess from device IDs alone.
2. Scan source read-only. Require no errors. Build plan in the existing external SQLite
   scratch: group order deterministic, keeper is MIN(path), others ordered by path;
   record root identities, per-path signatures and destination-relative mapping.
3. Preflight *all* operations: destination leaves/parents, name-limit and case/normalization
   aliases, metadata capability, source-removal permissions, destination space estimates,
   journal safety, and unsupported filesystem capabilities. Check encountered source
   directory identities against destination ancestors. A detected blocker yields zero
   moves and no destination/journal mutation. Linux source-removal parents must have
   neither APPEND nor IMMUTABLE inode flags. Creation ancestors must have only ordinary
   EXTENTS/INDEX directory flags and no project policy/inheritance; reject unsupported
   inherited metadata before staging or SQLite journal creation (ADR-005). These probes
   are read-only and use pinned descriptors, including nearest existing ancestors for
   missing suffixes. Space/permissions can change later.
4. Dry-run streams the checked plan and exits. Execute creates the new journal and
   required destination directories only now; persist the plan before the first copy.
5. For each victim, confirm root/parent/name identities and exact equality with the
   unchanged keeper, stream transfer, verify/publish, and only then unlink source.
   Recheck boundaries/identity before each mutation. Known directory/ctime changes
   caused by this run must be accounted for explicitly, never by disabling validation.
6. Persist final per-item and aggregate outcome. Successful execution means all N−1
   planned victims moved and one selected source keeper remains for every group.

No existing JSON inventory becomes mutation authority. Hashes may accelerate checks
but never substitute for exact byte comparison. The move report is a separate schema.

## File safety, metadata and concurrency

Use source/destination directory FDs, no-follow/nonblocking regular-file opens and
exclusive creation. All relative components come from validated enumeration; reject
absolute/empty/dot/parent traversal and unsupported filename encoding. Never trust
user-editable journal entries to perform later deletion.

Copy each victim to an exclusively created destination-filesystem staging file owned
by this operation. Record a relative staging identity in the journal. Compare source,
staging and keeper with bounded reads and before/after signatures; flush data and
required metadata. Publish the verified staging inode to its final path with an atomic
no-replace primitive; standard-library `os.link` with dir FDs is the initial candidate
for publication, followed by staging-link cleanup. Ordinary rename/replace is not a
safe no-clobber fallback. Filesystems without a validated primitive must fail closed.
Reopen/recheck final inode, bytes and metadata, sync its parent and persist destination
verification before unlinking the unchanged source name. Sync the source parent and
persist removal. Never remove source merely because a destination name exists.

Strict metadata policy includes mode/mtime plus preserving any attached ACLs, extended
attributes, ownership requirements, platform flags or auxiliary streams that would
otherwise be lost. Inode/ctime/link count cannot remain identical through relocation;
read-atime changes and loss of cross-root hardlink topology are explicit exceptions.
Implementation must inventory metadata with a platform-capability adapter; Python
`copystat` alone is not proof of complete preservation. If it cannot detect/preserve
an applicable class, fail before moving any file, naming the unsupported capability.
No silent fallback to dropping metadata. Use Linux/Synology capability evidence before
claiming that environment; unsupported metadata adapters block execution, not scanning.

Hardlinks count as distinct source paths; moving one may change keeper/sibling ctime.
Track all known inode aliases in the plan, re-prove bytes and refresh only changes
attributable to this operation. Keep identity/type/size/mtime/content checks effective.
Cross-volume destination files may be independent copies; do not report reclaimed bytes.

Require both trees and their ancestors to be exclusively managed for the operation:
stop backup/sync/ingest/edit jobs. Advisory operation locks coordinate this tool only;
they do not exclude arbitrary writers. POSIX stdlib offers no atomic conditional
unlink-by-inode, and checking a name then unlinking it has a race. Descriptor checks
reduce detected races but cannot guarantee safety against concurrent rename/write/mount
actors. Do not advertise such a guarantee. A snapshot of source alone is not enough
if execution later mutates a live namespace. If exclusive access cannot be established,
use dry-run only. This precondition and race limitation must appear in future CLI docs.

## Journal, cancellation and recovery

Use a new owner-only operation directory containing a durable SQLite journal (safe
synchronous mode) and root identity records. Report relative media paths only; no raw
exception strings, content or unsolicited absolute paths. Journal is sensitive local
operation state, kept outside Git and both trees. User-chosen shell output also belongs
outside both trees. Journal write/fsync failures stop all new source removals.

Per-item states: planned → copying → staged_verified → destination_verified →
source_removed. Persist intent before destructive transitions. Record staging/final
identities, expected metadata/content evidence, relative paths and stable error codes.
A crash between physical action and journal commit is explicitly ambiguous. Never
interpret an old planned/copying state as permission to erase a source or destination.

SIGINT stops scheduling and exits130 after best-effort durable state; no rollback.
SIGKILL/power loss may leave staging or duplicate paths. Recover by inspecting journal
and both trees, validating bytes and identities; automatic recovery commands are a
future design. Do not rerun with the same journal or overwrite prior destinations.
Even a fully verified destination is retained if source unlink fails. A crash or error
must prefer redundant copies to deleting the only known copy. Empty source directories
remain. Directory metadata may change due to legitimate moves; keepers' bytes remain.

## Diagnostics and user-visible outcomes

Stream JSONL to stdout to avoid a whole-plan memory list or pretending an interrupted
JSON array is complete. Version1 records: header (`operation`, `dry_run`), item (`keeper`,
`source`, `destination`, `size_bytes`, `status`, optional error `code`), and final summary
(`complete`, `planned`, `moved`, `bytes_moved`, `errors`). Paths are root-relative;
destination equals source-relative path, keeper is source-relative. Status is planned
for dry-run, moved only after removal, retained/error for failed execution. Header/items
without a terminal summary never certify completion. Counts are logical per path.

| Outcome | Exit and visible behavior |
| --- | --- |
| Successful dry-run or relocation, including no duplicate groups | 0; final complete=true; dry-run moved=0 |
| Incomplete scan, metadata/collision preflight blocker | 1; complete=false; moved=0; relative errors |
| Error after execution starts | 1; complete=false; accurate confirmed moves and journal; stop |
| Invalid mode/root/overlap/journal arguments, unsupported runtime | 2; no operations; generic diagnostic |
| SIGINT | 130; partial stream/journal must be inspected; no success claim |

Broken stdout/pipe stops scheduling; persist current state before further source removal
and exit1. Durable journal, not stdout, is recovery evidence. Diagnostics are concise
on stderr and avoid raw OS exceptions. Any journal failure after progress preserves
existing evidence and reports failure, never an empty-success result.

## Scale and operations

Owner workload is potentially hundreds of GB with no scan-time limit; no representative
file count, transfer throughput or NAS measurement exists. Index/plan/journal grow O(N)
on disk, transfer uses fixed-size buffers and bounded FDs. Copy verification adds multiple
full reads; no speed promise. Require free destination capacity for moved logical bytes
plus scratch/journal overhead. Conservative capacity estimates count hardlinks separately
and do not assume sparse-hole preservation or compression. Per-file staging does not
make the total destination capacity requirement disappear.

During implementation measure a bounded 10,000-small-file plan and a modest large-file
copy, recording environment, wall time, memory, scratch and destination usage. Add a
real two-device fixture for cross-volume behavior; a mocked EXDEV is not that evidence.
Actual file/directory fsync, no-replace publication and metadata capabilities require
early disposable probes; generic POSIX claims do not certify every NAS filesystem.

## Verification and acceptance matrix

All rows below are planned, not executed tests. Use original synthetic bytes and small
temporary trees, never personal media. Share recipes/expected outcomes across tiers.

| Requirement | Real-filesystem integration | Actual entry-point E2E | Demo |
| --- | --- | --- | --- |
| R1/R2 | a.jpg=100, nested/b.jpg=100 equal, unique.wav=50; keep a.jpg; only nested/b.jpg moves; group of3 and ordering/case/Unicode variants | Proposed CLI exact source/destination tree and report assertions | One source keeper, matching nested target, unique preserved |
| R1 | Empty duplicates and hardlinked members; self-induced ctime handled; no link-topology/reclaimability claim | Two and three-member groups including hardlinks | All selected aliases except keeper relocated |
| R3 | Same root, child, missing child, parent destination, symlink ancestors, aliases/bind mounts, prefix lookalikes | Invalid roots reject before scanner entry, journal or dest creation | Nested destination leaves both trees unchanged |
| R4 | Forced hash collision, incomplete permissions, file replacement, keeper mutation; zero moves on incomplete scan | Real non-root permission error blocks globally | No action from an incomplete inventory |
| R5 | Compare names/bytes/modes/mtime/link targets in both trees; nonexistent DEST/JOURNAL remain absent | Dry-run plan vs subsequent fresh execution; moved=0 | Inspect keeper and target paths |
| R6 | Existing file/dir/symlink/identical destination; late creation; case/Unicode filesystem collisions; no-clobber atomicity | Collision blocks or partial-fails honestly without overwrite | Existing target unchanged |
| R7 | Real separate filesystems; stage/source byte comparison; full metadata round-trip; no-replace failure | Cross-device CLI success with exact bytes/mode/mtime/metadata | Source removal follows verified target |
| R7/R8 | Disk-full/short-write/fsync/journal/metadata failure; source replacement at checkpoints; unlink failure | Controlled failure injection plus real permissions; all bytes accounted for | Failure retains source or verified destination |
| R8 | SIGINT/SIGKILL after copy/publication/unlink, reconcile disk vs journal; repeated fresh invocation conflicts safely | Subprocess checkpoints verify exits and surviving copies | Journal distinguishes confirmed and ambiguous operations |
| R9 | Large plan iterator, sparse capacity estimate, bounded transfer buffers | Legacy scanner suite/schema/exits unchanged | Scan-only command still read-only |

Test-data verdict **ADEQUATE for design feasibility**: synthetic recipes cover logical
cases; implementation environment plan must supply non-root Linux3.11/3.13 plus two
real writable filesystems. Existing CI filesystem/CLI discovery can collect new suites,
but CI setup must explicitly provision cross-device paths and metadata-capable fixtures.
Missing cross-device/ACL/xattr/no-replace/durability evidence blocks that implementation
support claim; a skip cannot close it. macOS is supplemental, not Synology proof.

Capture/probe trigger applies to newly relied-on no-replace/durability/metadata storage
behavior. Design-only delivery records the required early disposable probes; no new
platform support or successful probe is claimed. Implementation must run these before
committing to mechanisms. If stdlib/platform capabilities cannot meet strict metadata
requirements, return to SMELT for a justified dependency or narrower supported platform;
do not relax USER preservation requirements.

## Delivery, rollout and decisions

The design-only delivery ended at design-delivered. Implementation was subsequently authorized. Read [ADR-003](../decisions/003-move-dup-files.md)
on resumption, recheck base/source and early filesystem probes, then add new tests and
future CLI/docs. Existing scan inventory schema1 and summary remain unchanged. Full
forge implementation requires application checks, real integration, shipped CLI E2E,
adversarial review and a PR with verified CI; no merge authority is inferred.

## Open questions and risks

All requested USER behavior choices are resolved. Mechanism feasibility remains an
implementation gate: strict metadata detection, atomic no-clobber publication, directory
fsync and real cross-device verification must be demonstrated on each supported platform.
No ordinary live-filesystem implementation here can defeat arbitrary concurrent writers;
exclusive trees are a required operational precondition. Recovery is deliberately manual
and evidence-driven for v1. The accepted request permits designing future source-path
removal only after relocation; the subsequent implementation request authorizes code/tests/PR delivery, not a real-library run.

## Implementation contract refinement — 2026-11-18

USER authorized implementation and approved required metadata-inspection privileges and
new inode/creation time. Initial relocation adapter supports Linux ext4/tmpfs only,
requires effective root and CHOWN/DAC_OVERRIDE/FOWNER/SYS_ADMIN capabilities, preserves
uid/gid/mode/mtime and user.* xattrs, and rejects other namespaces/ACLs or unsupported
flags. Probe with statfs/statx and ext4 GETFLAGS; no generic unsupported-ioctl fallback.
Dry-run performs the same capability checks. macOS/other filesystems fail closed for
relocation; ordinary scan remains available. Linux CI must run privileged relocation
cases and a real ext4↔tmpfs transfer; local macOS checks cover legacy scan and invalid
root/mode behavior. New birth/creation time is an explicitly accepted exception.

No advisory namespace lock can exclude arbitrary writers. The CLI will require
`--exclusive-access` for execution as acknowledgement of the exclusive-tree precondition;
dry-run needs no acknowledgement. Source/destination directory locks additionally
exclude cooperative relocators. Journal parent must already exist; journal itself must
be new. Staging names are random reserved operation names; existing files are never
removed as cleanup unless their recorded inode matches this operation.


### ASSAY refinements

Initial tmpfs adapter support is withdrawn: volatile storage cannot satisfy archive/
journal durability and statx alone does not establish full tmpfs flag visibility. Current
execution/dry-run supports64-bit Linux ext4 only. CI provisions a second real ext4
filesystem in a loop-mounted image; different st_dev is asserted before cross-volume
E2E. `/dev/shm` is now an explicit refusal fixture. No btrfs/NAS support is claimed.
Destination must not contain actual/resolved default scratch storage; reject before
Scan creation, including dry-run. Existing destination roots reuse the already-held
lock instead of attempting a conflicting independent flock. Journal includes original
source/keeper signatures, SHA-256 candidate receipt (not standalone duplicate proof),
required metadata, staging/final identities and stable error codes. Source-removal gaps
are tested both by post-unlink journal failure and actual SIGKILL before the receipt.


### Final implementation evidence

All39 new behavioral tests (31 integration,8 E2E) pass in privileged Linux3.11/3.13 CI;
legacy suites run separately as non-root. See work-item evidence for precise skip/run
boundaries. SQLite native temp files are pinned to external scan scratch, verified by
PRAGMA and restored on exit; concurrent embedded SQLite users in the same process are
outside the single-writer CLI contract. Ext4 project IDs/xflags/extent policies are
explicitly queried and unsupported values rejected. Tests cover a substantial sort
and observed tree nonmutation, not direct physical-spill observation. Independent-agent
source challenge found no remaining grounded blocker; no human review or power-loss
certification is implied. PR#8 remains unmerged.


## macOS extension (2026-11-18)

The platform restrictions and strict metadata statements above describe the initial
Linux delivery. [macOS design](macos-relocation.md) and [ADR-004](../decisions/004-macos-relocation.md)
supersede those restrictions only for 64-bit macOS APFS: ordinary-user data-stream-only
relocation with resource-fork rejection; other metadata may be omitted by USER choice.
Linux preservation remains strict. Shared safety and journal requirements still apply.


### PR8 F1 correction
Static mutation permissions are part of global preflight, including ordinary-user
APFS ACL/sticky semantics and destination/journal creation ancestors. See the macOS
design R6 and [ADR-005](../decisions/005-relocation-permission-preflight.md). No write
probes occur during dry-run. Inheritable ACL creation layouts are explicitly rejected;
subsequent permission changes retain the documented partial-failure contract.
