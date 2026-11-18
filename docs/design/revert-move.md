# Revert move

**Status:** Implementation in verification — no merge authorized

## Problem and current state

USER requests restoring files relocated by an earlier move to their original locations,
using the relocated root plus an explicit revert flag, with dry-run. This delivery is
artifacts only. [Brief](../../work-items/revert-move/brief.md),
[ADR-006](../decisions/006-revert-move.md) and
[evidence](../../work-items/revert-move/evidence.md) record scope and attribution.

At baseline4af6c1f, `dup_media/__main__.py:18–34` exposes scan/move only. The external
SQLite journal (`move_journal.py:33–45`) stores source/destination dev/ino, relative
victim/keeper paths, metadata, signatures and SHA256; it lacks original-root pathname,
discovery information, format version and an operation-completion marker. Archive-only
legacy discovery is therefore impossible. Existing transfer (`relocate.py:218–305`)
requires a duplicate keeper; reversing its arguments or rerunning duplicate detection
would omit sole archive copies. Source unlink, receipt and stage cleanup are separate
actions. Existing automatic recovery is explicitly absent.

## Requirements and non-goals

- **R1 — Explicit restoration:** new `--revert-move ARCHIVE` mode restores only the
  selected completed move's recorded paths beneath its original root. Restore files
  regardless of current extension filters; do not require a surviving duplicate keeper.
- **R2 — Discovery/compatibility:** future moves write a self-contained, versioned
  recovery manifest discoverable under ARCHIVE. Legacy moves require both
  `--original-root ORIGINAL` and `--move-journal OLD_OPERATION_DIRECTORY`.
- **R3 — Matching directory structure:** every ordinary subdirectory beneath ARCHIVE
  must already exist as a real directory at the same relative path under ORIGINAL.
  Extra ORIGINAL directories are allowed. Exclude only the validated reserved recovery
  control tree. Never create missing restoration directories. Any mismatch aborts the
  whole plan with zero file/control mutation. This checks directories, not equal file
  sets: keepers and unrelated original files are expected to remain.
- **R4 — No overwrite:** any existing restoration leaf, including an identical file,
  directory, symlink or special entry, aborts the whole plan before mutation. No skip,
  replace, merge or automatic rename. Unregistered archive files remain untouched.
- **R5 — Dry-run:** validate the same operation, directory, content and permission
  conditions and stream the plan without changing either tree or any persistent receipt.
  Ordinary read-atime effects are outside the no-mutation promise.
- **R6 — Completed operations only:** refuse incomplete/ambiguous forward moves and any
  started-but-not-completed revert. No automatic resume, interrupted-move reconciliation
  or batch rollback. A completed revert is reported as already reverted, without mutation.
- **R7 — Fresh proof:** check current roots, parents, archive identities/content and
  capabilities; copy to a restoration stage, compare live bytes exactly, durably publish
  without replacement, then remove only the freshly revalidated archive entry.
- **R8 — Durability/errors:** record revert intent/progress durably, stop on first late
  failure, preserve at least one verified copy and truthful confirmed/uncertain outcomes.
- **R9 — Policy/privacy:** retain supported64-bit Linux ext4 strict metadata and macOS
  APFS data-only behavior and exclusive access. Ordinary scans stay read-only. Report
  relative media paths and stable errors; do not emit stored absolute paths by default.
- **R10 — Scale/verification:** bounded streaming and external disk-backed indexing;
  real filesystem integration and shipped-entry-point E2E on both native platforms,
  including real second volumes and failure cases.

Non-goals: restoring metadata previously discarded on macOS, original inode/birthtime/
hardlink topology, directory pruning, arbitrary new restore roots, archive relocation to
another filesystem, filesystem-wide inode searches, approximate proof, imports from
unrelated mover tools, unsupported NAS/btrfs/SMB/exFAT support, GUI, uploads or media decoding.
Design-only scope grants no application implementation, actual file operations or merge.

## Alternatives and recommendation

1. Reverse the existing duplicate scanner: rejected because archive paths can be unique
   and keepers may be changed/deleted. It does not establish provenance or original root.
2. Always require original root and external journal: viable legacy path, but fails the
   desired future root-only interface.
3. **Selected:** versioned self-contained per-operation recovery manifest for future
   moves; explicit original root plus existing journal for legacy terminal-consistent
   operations. Extra control data and a forward-writer change are necessary costs.
4. Store only an external journal pointer: rejected as the primary future mechanism;
   root-only recovery would still depend on a missing/moved external directory.
5. Create missing restore folders or merge/overwrite existing files: rejected by USER's
   directory-matching and never-overwrite clarification.

## CLI and visible behavior

Implemented feature-branch interface (delivery/CI pending):

```sh
# Future manifest-backed operation: only location input is the archive root.
python3 -m dup_media --revert-move ARCHIVE --dry-run
python3 -m dup_media --revert-move ARCHIVE --exclusive-access

# Legacy operation, with explicit provenance locations.
python3 -m dup_media --revert-move ARCHIVE --original-root ORIGINAL \
  --move-journal OLD_OPERATION_DIRECTORY --dry-run
python3 -m dup_media --revert-move ARCHIVE --original-root ORIGINAL \
  --move-journal OLD_OPERATION_DIRECTORY --exclusive-access
```

Keep ROOT positional; `--revert-move` is a boolean mutually exclusive with
`--move-duplicates`. Revert rejects `--destination`, `--extensions` overrides and the
forward-only `--journal`. The legacy argument pair is all-or-nothing and is used only
when no valid manifest exists; never override a manifest binding or silently fall back
from malformed new metadata. Execution requires `--exclusive-access`; this is an
acknowledgement, not a second location input or a locking guarantee. No external new
journal path is required: locations are derived as described below.

With multiple recorded operations, implicit selection requires exactly one operation
and no unresolved operation in that archive. Otherwise list opaque operation IDs and
require `--operation ID`. Never select by latest timestamp. An explicitly selected
completed operation still fails if unresolved records overlap its paths/roots or safe
isolation cannot be established. Selection never means all operations. A manifest root
may contain independent operations/original roots; do not infer one common original root.

JSONL schema1 header: operation=`revert_move`, operation_id, provenance=`manifest-v1`
or `legacy-journal`, dry_run, metadata_policy. Items include root-relative archive/source
path, same restoration-relative path, size_bytes and status=`planned` or `restored`.
Summary: complete, planned, restored, bytes_restored, errors. Do not equate counts with
physical storage savings. Only confirmed durable states count as restored; an action/
receipt gap is an incomplete result even if live files appear restored.

| Outcome | Exit/result |
| --- | --- |
| Valid dry-run or successful revert |0; complete=true; dry-run restored=0 |
| Structure mismatch, existing target, changed archive, invalid operation state or other checked preflight blocker |1; complete=false; restored=0; no persistent mutation |
| Failure after execution starts |1; complete=false; confirmed progress plus receipt; stop |
| Already reverted with valid completed receipt |0; complete=true; restored=0; reason=already_reverted |
| Invalid arguments, unavailable root/control input or unsupported runtime |2; generic concise diagnostic; no operations |
| SIGINT |130; incomplete operation, inspect receipts manually |
| Broken output pipe |1; stop before further archive removals; preserve receipts |

Stable error examples: recovery_missing, recovery_unsupported_version,
recovery_ambiguous, recovery_invalid, root_identity_mismatch, operation_incomplete,
revert_incomplete, structure_mismatch, restore_target_exists, archive_changed,
insufficient_space, permission_denied, durability_failure. Error paths are relative to
an identified root; do not print raw OS exceptions containing private absolute paths.

## Provenance format and forward-writer dependency

AGENT design: reserve `ARCHIVE/.dup-media-recovery/`. It is a non-symlink owner-only
control directory, not a media candidate or a restoration subfolder. It contains a
versioned root marker and `operations/<UUID>/manifest.sqlite`. No pickle, embedded code,
SQLite extensions, triggers or executable instructions. New forward moves preflight
reserved-name/media-path collisions and foreign/corrupt control trees; never repurpose
user content. Existing move dry-run still creates nothing. This dependency must ship
with revert: documenting root-only restoration without the writer would be incomplete.

A manifest is self-contained and streams tables rather than a giant JSON list:

- operation: format_version1, operation UUID, creation platform/policy, source original
  absolute root locator and dev/ino, archive dev/ino, forward state, item count;
- items: unique safe relative path, original metadata contract, size, SHA256, final archive
  signature/dev/ino, and recorded forward stage basename/identity for consistency checks;
- revert: separate immutable attempt identity and durable status/receipt references.

Record the original root's descriptor-resolved physical absolute path. Dev/ino validate
identity but are never used to search the machine. Archive root supplied at revert must
match its recorded identity; same-filesystem renaming can retain identity, while copied
or cross-filesystem relocated archives are refused in v1. Original root must exist at
its recorded locator with matching identity; moved/recreated roots require manual recovery.

Forward protocol addition: after whole-plan validation, durably create a PENDING manifest
before the first media removal, alongside the existing external forward journal. Populate
candidate records before progress; primary journal continues existing per-file states.
After all files are transferred and staging aliases cleaned, validate final archive
signatures/content and all receipts; durably commit manifest COMPLETE. Only then may
forward output claim complete. Failure to create/finalize provenance fails the operation
honestly, possibly after progress, with PENDING remaining for manual inspection. Never
infer COMPLETE from a partially written manifest. Empty forward plans preserve existing
no-destination/no-journal-creation behavior and produce no recoverable operation.

Use SQLite FULL synchronization, fsync control directories, and Darwin fullfsync where
applicable. Required native capabilities are implementation gates, not a durability
claim from design. No physical power-loss certification. SQLite input is untrusted:
open read-only without creating sidecars during preflight, disable extension loading,
validate schema/tables/types/version and bound strings/rows-per-step, and plan into an
external private database rather than execute queries/schema supplied by the input.
No database rewrite or silent migration during dry-run. Runtime SQLite must be supported.

Private absolute locators are an intentional local recovery-record disclosure; protect
files0600/directories0700 and compatible non-inheriting native ACLs. Never include these
records in Git or normal stdout. Ownership/permissions/schema/identity checks reduce
accidental misuse but do not authenticate a maliciously rewritten record by the same
user/root. This is a trusted-owner local recovery tool, not a forensic import boundary;
explicit invocation must use that owner's recovery record, with fresh safety checks.

## Legacy eligibility and completion semantics

Legacy mode uses the explicitly supplied existing external journal read-only; it must
match both supplied root identities and the recognized historical schema. Freshly
validate every journal item, not just a filtered subset:

1. Every row is `source_removed`, with no recorded error and valid metadata/path/digest.
2. Every original target is absent; every archive file exists and matches recorded
   published dev/ino, size, digest and supported preserved metadata. Account for expected
   forward staging-unlink ctime change; do not compare original pre-move signature to
   the new archive inode or demand a ctime value the old writer never recorded.
3. Every recorded staging alias is absent; no contradictory state or incomplete revert
   receipt exists. All directory, root and safety checks also pass.

Define **completed legacy move** as this fully terminal, freshly consistent on-disk
operation. Old formats cannot prove a successful process exit, nor distinguish a kill
after the final durable cleanup from normal exit; this is explicitly not such a claim.
Any copying/staged/destination_verified row, lingering stage, missing archive, present
original or receipt/action ambiguity is refused for manual recovery; do not repair,
resume or infer missing rows. Unsupported older schemas fail rather than guess.

This interpretation supports USER's legacy requirement without pretending old records
have new completion fields. Future manifests require their explicit COMPLETE marker.
A completed original root containing unrelated files is normal; only planned restore
leaves must be absent. No provenance can undo metadata already discarded or establish
legitimacy of arbitrary user-edited paths without an authenticated historical source.

## Planning, directory validation and execution

Implement a dedicated `Revert` planner/reader; likely new `dup_media/revert.py` and
`dup_media/recovery.py`. Reuse reviewed descriptor/location/platform primitives after
extracting only narrowly shared copy/no-replace/durability helpers as needed. Do not
call the duplicate-dependent `Relocation.transfer` unchanged.

### Read-only global preflight

1. Parse mode and provenance; pin archive, original and control/journal locations.
   Refuse equal/overlapping roots in either direction, symlink ancestors, physical aliases,
   unsafe/nested mount layouts and scratch aliases before scratch creation or traversal
   that could escape roots. Both roots already exist. Preserve default read-only scanning.
2. Validate operation selection/state and input snapshot in read-only mode. Pin immutable
   schema/record snapshot plus database identity so replacement during planning is caught.
3. Walk ARCHIVE directories descriptor-relatively, excluding only the validated control
   subtree. Every other directory, including empty/unregistered subfolders, requires an
   existing matching ORIGINAL directory. Extra ORIGINAL directories are not enumerated
   for equality. Reject symlink/special directory aliases or invalid encodings; do not
   follow them. Never mkdir the restore tree. Use an external SQLite directory identity
   index for bounded-memory comparison. Recorded directories cannot replace live checks.
4. For every registered file validate relative components (no absolute/`..`/NUL/control
   escape), unique targets, case/normalization aliases, ordinary regular-file identity,
   size/digest and metadata. No extension filtering or unregistered-file relocation.
   Existing restore leaves of any kind are global blockers. Freshly validate archive
   bytes against recorded fingerprint as a change detector; fingerprint equality alone
   never authorizes archive deletion.
5. Preflight every archive source-removal and original existing-parent creation/cleanup
   permission, Linux parent APPEND/IMMUTABLE/project flags and Darwin ACL/sticky/inheritance
   policy. Estimate full logical restore size (hardlinks separately) plus bounded scratch/
   receipt overhead. Validate revert-control creation and database/durability capability.
   A late-listed static blocker still produces zero moves and no receipt mutations.
6. Dry-run streams the checked plan and exits. Execute revalidates snapshots after taking
   cooperative root/control locks and before creating durable STARTED intent. Exclusive
   namespace access by the user remains required; no atomic arbitrary-writer exclusion.

Example: ARCHIVE directories `{nested, nested/2025}` require both under ORIGINAL.
ORIGINAL may also contain `keepers` and empty folders. Missing `nested/2025`, or a symlink
at that location, aborts before any restoration. Existing `ORIGINAL/nested/b.jpg` aborts
even if bytes match. Extra archive files are not moved, but their real subdirectories
participate in the structural rule. Control metadata alone is excluded.

### Revert receipts and transfer

For manifest-backed operations, create a new append-only attempt receipt under the
reserved operation control directory; for legacy, use a fixed new `revert/` child of the
supplied external journal directory, preserving the original journal.sqlite bytes.
Check/control that namespace before progress; an existing incomplete attempt refuses
further automatic execution. No new location argument is necessary. A stable durable
STARTED record must precede any archive unlink. Dry-run opens all inputs read-only and
never creates this record. Future forward journals remain external as before; reverse
receipts inside a reserved non-media archive control tree are an explicit new exception.

Per file: revalidate archive/root/parent signatures; stage a new file beside the absent
original leaf using O_EXCL/no-follow; copy with fixed buffers; compare fresh archive
and stage streams exactly; apply/check the selected metadata policy; sync; publish
without replacement using validated no-clobber primitives; sync original file/parent;
persist restore_verified; revalidate live archive and restored bytes, identities,
metadata and all pinned names immediately before archive unlink; unlink only that
archive name; sync archive parent; persist archive_removed; clean restoration stage
and sync. Keep confirmed states separate from physical action/receipt gaps. Account for
self-induced hardlink ctime changes in the disk-backed index, as existing mover does.
Do not require the old duplicate keeper, delete source directories or clear inode flags.

After every planned item is durably archive_removed and stages cleaned, commit COMPLETE
revert receipt, then emit successful summary. If any late error occurs, stop without batch
rollback; preserve stage/receipt and remaining archive files. Previously restored files
remain. Any subsequent attempt finding STARTED/incomplete state refuses even if a human
could reconcile it; manual recovery is the explicit v1 policy. If final completion commit
fails after file work, report incomplete, not success. Already-completed revert is a
read-only already_reverted result only with a valid completed receipt and consistent
restored state; contradictions fail closed. Archives/control records are retained.

## File safety, metadata, operations and resource bounds

Linux preserves supported archived uid/gid/mode/mtime/user.* metadata and rejects unsupported
attached metadata; macOS preserves main-stream bytes only and rejects resource forks or
unsupported flags as in ADR004. Restoration uses metadata available under that policy,
never invents original values. New inode/creation time and changed hardlink topology are
allowed. Exact archive-to-stage/final comparisons, not hashes or old journals alone,
authorize removal. Unrelated archive files, original keepers and old receipt data remain.

Let N be operation entries, D archive directories and B registered logical bytes. Use
O(N+D)disk for validated provenance/plan/alias/identity indexes and receipts, bounded
record/metadata sizes, fixed1MiB byte buffers and bounded descriptors; traversal memory
may depend on directory depth, not all entries. Stream/sort on external SQLite, not
Python whole-manifest lists. A fixed number of full byte passes over B is acceptable;
no duplicate all-pairs search. Reserve conservative capacity; later disk exhaustion is
still possible. Cancel between records/chunks and before each removal. No benchmark or
NAS/hardware durability measurement is claimed.

## Verification and acceptance matrix

All rows are **planned**, not passing tests. Generate original literal bytes in disposable
trees; media suffixes exercise selection/history, not decoding. New writer/reader must
round-trip actual generated manifests. Legacy fixture provenance is the inspected old
writer/schema, never invented original-root fields. No private collection, credentials
or licensed sample download required. Test-data verdict **ADEQUATE for design**: native
ext4/APFS and second-volume CI recipes exist; implementation must actually execute them.

| Requirement | Real-filesystem integration assertions | Actual entry-point E2E assertions | Demo outcome |
| --- | --- | --- | --- |
| R1 | Actual forward move then revert; exact original paths/bytes restored; keeper may be absent/changed; unique/unregistered files untouched | Run proposed `-m dup_media --revert-move`; actual subprocess, no duplicate-regroup shortcut | nested/b.jpg returns to original location |
| R2 | Future writer manifest round trip; explicit legacy roots/journal; multiple IDs, missing/corrupt/version/root mismatch; no silent fallback | Root-only success for one new operation; legacy pair required; ambiguity requires ID | no original path entry for new manifest |
| R3 | Matching nested/empty archive directories; extra original directories allowed; missing/mismatched/symlink late directory aborts with whole-namespace equality | Same cases in dry-run and execution, no restore-directory creation | mismatch restores zero files |
| R4 | Identical/different/file/directory/symlink target, including later path; no overwrite, no journal mutation | Exact nonzero exit/error/moved=0 and full namespace preservation | existing target blocks plan |
| R5 | Compare both full trees and persistent DB/control bytes/identities before/after preview; allow read-atime only | Shipped dry-run creates no stage/receipt/dirs | inspect planned paths only |
| R6 | New PENDING marker; legacy incomplete/error/missing stages or receipt/action gaps; interrupted revert; completed no-op and contradictory receipt | Real SIGINT/SIGKILL at boundaries, subsequent invocation refuses; complete receipt repeat harmless | manual recovery required after interruption |
| R7/R8 | Real second volume; file/root/control replacement, same-size changed bytes, copy/metadata/fsync/journal/unlink faults; retained verified copy; no-clobber race | Native subprocess success/error/signal exits with accurate confirmed progress | no archive removal before verified restore |
| R9 | ext4 strict metadata, parent flags/project inheritance and ACLs; APFS data-only/forks/sticky/inheritance; hardlinks/zero/Unicode; unsafe roots/scratch/mount aliases | Generic private-path-free diagnostics; exclusive-access required; old scan/move contracts unchanged | policy clearly identified |
| R10 |10k registered items/deep dirs, fixed-buffer/descriptor bounds and disk indexes; capacity/logical sparse sizes, cancellation | Broken pipe and bounded plan stream with unrelated files untouched | scalable plan, honest partial result |

Extend `.github/workflows/application.yml` mandatory Linux privileged discovery, currently
only `test_relocate*.py`, to include revert integration/E2E modules; otherwise optional
non-root skips are not proof. Include native macOS revert modules in mandatory APFS runs,
currently `test_macos*` integration and full E2E, with distinct-device assertions and
missing-prerequisite failures. Keep ordinary permission suites separate from root runs.
Record injected failures as injected; actual signal delivery as real at an injected
observation checkpoint; never claim disk-full/power-loss hardware evidence from mocks.

Implementation checks: compileall/help/application CLI contracts; all affected filesystem
integration and shipped CLI suites; forge artifact check; framework tests for tooling
changes. Scope affected reruns after adversarial code-review/test-realism audits. Native
hosted runs on Python3.11/3.13 close platform gaps only when evidenced for that commit.
Plan10k-entry revert dry-run wall/index/RSS and16MiB distinct-device transfer measurements;
no arbitrary latency target or borrowed forward-move timings.

## Delivery, rollout and decision records

Deliver together: provenance writer/versioning and final-completion rule, revert parser/
planner/transfer/receipts, CLI/docs, native tests and required CI discovery. Do not enable
root-only syntax before the writer produces usable self-contained records. Do not rewrite
legacy journals or silently upgrade historical archives. Old completed operations use
the explicit legacy path; unsupported states/formats require manual recovery.

[ADR-006](../decisions/006-revert-move.md) attributes USER choices and AGENT mechanisms.
ADR003's no-overwrite/fresh-proof/exclusive-namespace and ADR004–005 platform policies
remain; this design adds an explicit recovery mode rather than changing scan defaults.

Design-only handoff: work-item phase design-delivered; no application implementation or
runtime proof. Resume implementation with SMELT/fixture reassessment, then normal FORGE,
TEMPER, ASSAY and STAMP. No consequential USER question remains. Implementation must
validate native durability/control DB behavior and bounded parser limits; if unavailable,
report the prerequisite rather than weaken fail-closed safety. Retain the explicit legacy
completion-evidence limit and same-user provenance trust assumption. Revisit for signed
portable manifests, moved roots, interrupted-operation recovery or additional filesystems.


## Implementation receipts (2026-11-18, AGENT)

USER resumed with `/forge implement revert-move`. New recovery.py and revert.py implement
versioned protected SQLite records and a separate recorded-path planner. Existing move
journal schema is unchanged. Read-only SQLite inputs reject sidecars/schema objects;
mutable scratch/spill remains outside operation trees. Implementation conservatively
refuses any unresolved operation in an archive even with an explicit selector, rather
than claim partial-operation isolation. Text records are capped at2MiB, paths4096UTF-8
bytes. Full final CI/review evidence is maintained in the work item, not inferred here.
