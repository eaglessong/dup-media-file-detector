# ADR-006: Explicit completed-move restoration

**Status:** Accepted for design; not implemented
**Decided by:** USER (requirements/choices), AGENT (mechanisms below)
**Date:**2026-11-18
**Feature:** revert-move

## Context and options

USER requested a work item/design only: restore previously relocated files to original
locations by supplying the relocated root and a revert flag, with dry-run. Existing
move journals record root inode identities and relative paths, but no original absolute
root, discovery or completion marker. A duplicate scan cannot identify restoration
candidates because archive copies may be unique. Current recovery is manual.
See [design](../design/revert-move.md) for source receipts, alternatives and acceptance.

## USER decisions

Actual SURVEY answers, retained verbatim:

1. “Support future root-only reverts with a recovery manifest; existing moves require
   the original-root path and journal (Recommended)”
2. “Check whether the folder structure under the original file path is the same as the
   one of the new root folder. If yes, just put the files under the corresponding
   subfolder within original root path; if not, bail out without changing anything.”
3. “Revert completed moves only; refuse interrupted moves or reverts for manual recovery
   (Recommended)”
4. Clarification: “Yes—require matching archive subfolders; allow extra original folders;
   never overwrite files (Recommended)”

Thus missing/mismatched archive-relative ORIGINAL directories block the whole plan;
original extra directories are valid; no restore-directory creation and no overwrite,
even for byte-identical existing target leaves. This does not require identical file
sets or delete original keepers. No personal-media operation is authorized now.

## AGENT decisions and rationale

- Separate `--revert-move` from scan/forward move. Plan registered paths, not duplicate
  groups; fresh content/identity checks and exact copy comparison authorize removals.
- Future forward moves write a self-contained versioned SQLite manifest under reserved
  archive control `.dup-media-recovery/`, with original physical root locator/identity,
  operation UUID/policy/items and a durable COMPLETE marker after final stage cleanup.
  Existing external forward journal remains. PENDING means manual recovery, not infer
  success. Preflight foreign control/path collisions; dry-run creates nothing.
- Root-only means only one location input; execution still requires `--exclusive-access`.
  Ambiguous multi-operation archives need `--operation`, not timestamp guessing.
- Legacy requires `--original-root` plus `--move-journal`. Define completed legacy as
  fresh terminal on-disk consistency of every recognized journal row: source_removed,
  no error/stage, absent original leaves, present validated archive copies/root bindings.
  Never claim old records prove a successful command exit; a kill after final cleanup
  is indistinguishable. Any contradictory/intermediate state is refused, not repaired.
- Directory matching walks all ordinary archive directories, including empty/unregistered
  subfolders, excluding only validated reserved control data. Extra original folders
  do not matter. Never move unregistered files or prune directories.
- Use staged verified no-clobber publication then archive removal, bounded streaming/
  external SQLite, whole-plan permissions/flags/ACL/project/capacity preflight, live
  root/name pins and late revalidation. No batch atomicity or arbitrary-writer guarantee.
- Derive revert receipts under reserved manifest control or a new `revert/` child of the
  legacy external journal directory, so no extra receipt path argument is required.
  Preserve original move receipt data. This explicitly permits reverse receipts in
  reserved archive control, while forward journals retain their external-location rule.
  A started/incomplete revert is manual-only; completed repeat is read-only no-op only
  when its live state is consistent. Never automatically delete its control records.
- Reuse Linux strict and macOS data-only policies. Metadata lost by the earlier move,
  original inode/creation time and hardlink topology cannot be reconstructed.
- Persisted private locators stay local with owner-only permissions, not stdout/Git.
  Schema/path/identity validation and live proofs do not authenticate malicious edits
  by the same owner/root; trusted-owner records and exclusive access are preconditions.

These are attributed technical choices, not additional USER quotes. Alternatives:
mandatory legacy-style arguments conflict with desired future interface; a pointer-only
manifest still depends on the external journal; exact directory-set equality conflicts
with clarified extra-original-folder allowance; automatic partial reconciliation is
explicitly outside this version.

## Consequences, rollback and revisit

Root-only restoration requires updating future forward moves as part of implementation;
legacy archives are not silently upgraded. New control data contains private absolute
root locators. A complete legacy filesystem state does not establish historical process
exit. Originals must remain at their recorded root identity/locator; copied archives,
recreated/moved original roots, unsupported metadata and ambiguous operations fail closed.
Revert may leave extra copies and incomplete receipts after late failure; manual recovery
is intentional. Native durability, parser trust restrictions and CI discovery must be
validated during implementation, not asserted from a document.

No existing application behavior changes in this design delivery. Revise this ADR/design
before implementation if choices change; keep the prior record when superseding. Revisit
for portable/signed manifests, alternate restore roots, partial recovery, new platforms
or a broader metadata policy. ADR003–005 remain in force except the explicit additional
reverse-control receipt location and new designed restore mode. No implementation,
GitHub publication, merge, release or media mutation is authorized by this delivery.
