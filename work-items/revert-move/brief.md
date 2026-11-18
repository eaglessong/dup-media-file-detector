# Revert move

**Status:** Implemented on feature branch — verification/review/PR pending

## Goal and USER requirements

USER: `/forge create a work item named revert-move and the related design. Do not
implement.` Restore files relocated by a prior move to their original locations,
using a relocated-root argument and an explicit revert flag, with dry-run.

Accepted SURVEY:

- Future moves carry a discoverable recovery manifest for root-only reverts. Existing
  moves require the original-root path and external move journal.
- Every archive subfolder must exist at the matching relative path under the original
  root. Extra original folders are allowed. Structure mismatch aborts without changes.
- Never overwrite existing files; no restoration-directory creation.
- Revert completed moves only; interrupted moves/reverts require manual recovery.

Verbatim answers and attributed mechanisms: [ADR-006](../../docs/decisions/006-revert-move.md).

## Example and proposed interface

A prior move put `ORIGINAL/nested/b.jpg` at `ARCHIVE/nested/b.jpg`. Revert validates that
`ORIGINAL/nested` already exists, that b.jpg is absent there and that archive bytes and
provenance are valid. It copies/verifies/publishes the restored file before removing
its matching archive name. Other original files and unregistered archive files remain.

Proposed, **not shipped**:

```sh
python3 -m dup_media --revert-move ARCHIVE --dry-run
python3 -m dup_media --revert-move ARCHIVE --exclusive-access
# Legacy adds both --original-root ORIGINAL and --move-journal OLD_OPERATION_DIRECTORY.
```

## Acceptance criteria

- R1–R2: explicit restoration of registered paths; new manifest discovery and safe
  explicit legacy support. No duplicate re-scan or keeper dependency.
- R3–R4: archive-directory subset matches original directories; no overwrite; any static
  mismatch/conflict aborts the whole plan before persistent mutation.
- R5–R6: faithful no-mutation dry-run; completed-only operation/receipt eligibility;
  incomplete attempts fail for manual recovery.
- R7–R8: fresh exact bytes/identities and durable no-clobber copy precede archive removal;
  late errors stop with retained copies and honest receipts.
- R9–R10: current native ext4/APFS metadata/privacy/safety policies, bounded resources,
  actual filesystem integration and shipped-entry-point E2E verification plan.

See the [design](../../docs/design/revert-move.md) for full numbered requirements,
legacy completion-evidence limits, CLI/errors, provenance/state machines and acceptance matrix.

## Boundaries and next step

No consequential USER question remains. AGENT choices include conservative operation
selection, reserved versioned SQLite control, derived revert receipt locations and
fresh terminal-consistency eligibility for old journals that cannot prove process exit.

No implementation, test/CI changes, original-file operation, PR publication or merge.
No automatic partial resume/rollback, alternate restore roots, overwrite, directory
pruning, platform expansion, original inode/topology recovery or restoration of discarded
macOS metadata. Resume with SMELT and fixture reassessment before implementation. This
work item depends on future forward-move manifest writing; legacy mode stays explicit.


## Implementation resume

USER `/forge implement revert-move` now authorizes implementation/tests/PR delivery,
not merge or personal-file operations. Earlier design-only scope above is historical.
Current native implementations and evidence are in recovery.py/revert.py and evidence.md;
future forward moves write self-contained records. Do not treat pending CI/review as
completion. Existing untracked move.json remains unread/unmodified.
