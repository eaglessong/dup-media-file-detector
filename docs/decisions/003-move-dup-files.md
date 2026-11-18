# ADR-003: Explicit relocation of exact duplicate paths

**Status:** Accepted behavior; proposed implementation mechanisms
**Decided by:** USER (requirements/choices) and AGENT (technical decisions below)
**Date:** 2026-11-18
**Feature:** move-dup-files

## Context and options

Existing read-only scanning proves exact groups but has no move capability. Relocation
changes source names, may cross filesystems and can fail partway through. Options include
choosing keepers interactively or deterministically, using stale inventories or fresh
scans, and restricting moves to one device or supporting verified copies across devices.
See the [design](../design/move-dup-files.md) for feasibility and failure contracts.

## Decision and rationale

USER request: “create a work item named move-dup-files and the related design. Do not
implement.” The requested future behavior keeps one copy in each duplicate group,
relocates the others to a CLI-supplied root outside the scanned folder, preserves
relative directory structure, and supports dry-run.

Actual USER SURVEY answers:

- “Keep the first root-relative path in deterministic alphabetical order (Recommended)”
- “Yes—copy, verify, then remove the source; retain the source on failure (Recommended)”
- “Scan afresh, then plan and move; dry-run shows the plan (Recommended)”
- “Preserve bytes, permissions and modification time; reject files with metadata the tool cannot preserve (Recommended)”

AGENT technical choices:

- Interpret deterministic alphabetical order as SQLite BINARY order of valid UTF-8
  root-relative paths, case-sensitive, without normalization; do not infer depth/age preference.
- Introduce explicit `--move-duplicates SOURCE --destination DEST`, with `--dry-run`
  or an execution-only external `--journal`. Existing invocation remains read-only.
- Reject overlap in both directions, equal roots, symlink ancestors, unsafe aliases
  and unvalidated mount layouts. Never overwrite, even identical existing targets.
- Abort globally on incomplete scans and detectable preflight conflicts; stop on first
  execution failure without batch rollback. A late failure may leave extra copies.
- Initially use one staged copy/verify/no-replace-publish/remove protocol on both same-
  and cross-device moves. Candidate no-replace mechanism is descriptor-relative link
  publication; capability probes must validate it, with no overwrite-capable fallback.
- Keep a durable external journal; manual recovery only in v1. Do not trust saved
  inventories or journals as fresh deletion authority. No empty-source-directory cleanup.
- Treat every hardlink as a selected path; destination topology may differ. Do not
  claim physical savings. Account explicitly for self-induced inode/dir metadata changes.
- Require exclusive source/destination namespaces; stdlib path checks cannot atomically
  exclude arbitrary concurrent rename/write/unlink races. Dry-run is the available mode
  when exclusive access cannot be established.
- Strict metadata capability is fail-closed. Bytes/mode/mtime alone or `copystat` alone
  cannot certify ACL/xattr/flags/ownership/auxiliary-stream preservation. Unsupported
  detection/preservation blocks execution until implemented or separately redesigned.

These defaults favor observable, recoverable failure over silent overwrite/metadata loss.
They are not additional USER quotes or permission to act on real media now.

## Rollback or reversibility

This delivery changes documents only; revise before implementation if requirements
change. A future completed relocation can be manually reversed only after fresh identity,
byte and conflict checks. No automatic rollback or power-loss atomicity is promised.
Keep prior decisions: ADR-001's scan stays read-only and its fresh-proof restriction
still applies; ADR-002's scan summary remains logical bytes and unchanged. This record
adds a separately explicit future mutation mode rather than changing scan defaults.

## Consequences and revisit trigger

Extra I/O, destination capacity, external journal and exclusive access are operational
costs. Cross-device/metadata/no-replace/durability support requires real disposable
filesystem evidence before implementation completion; NAS hardware is unverified.
Revisit if strict metadata requires a new dependency/platform adapter, publication
cannot satisfy no-clobber, concurrency is required, or automated recovery is requested.
No code implementation, original-file operation, PR publication or merge is authorized
by this design-only delivery.

## Implementation SURVEY / SMELT — 2026-11-18

USER resumed with `/forge implement move-dup-files`. Implementation/test/PR delivery
is now authorized, but no real-library operation or merge is requested.

New actual USER answers to feasibility questions:

- “Yes—require the capabilities needed to inspect and preserve metadata (Recommended)”
- “Yes—allow new inode/creation time; preserve and verify the other metadata (Recommended)”

AGENT implementation scope: Linux ext4 and tmpfs initially, with effective root plus
CHOWN/DAC_OVERRIDE/FOWNER/SYS_ADMIN capabilities for strict metadata inspection. Detect
all xattr namespaces; preserve user.* and reject other attached namespaces, ACLs and
unsupported inode flags. Preserve uid/gid/mode/mtime. Refuse other filesystems/platforms
in relocation (including dry-run); scan-only stays portable. Creation time joins the
explicit inode/ctime/link-topology exceptions by USER choice. Validate storage primitives
with disposable Linux CI fixtures; no Synology hardware claim. Supporting btrfs/NAS or
additional attached metadata is a future adapter, not an implicit fallback.


### ASSAY safety refinement (AGENT)

Restrict initial relocation to64-bit Linux ext4. Earlier tmpfs support is superseded:
volatile destination/journal cannot meet the durable archive intent; ext4-only also
avoids an unestablished tmpfs flag-visibility premise. Cross-volume remains supported
and tested on two real ext4 filesystems, not mocked EXDEV. No USER requirement is relaxed.
Journal now retains original signatures/digest and stable errors; observed existing-root
lock and scratch-overlap defects are fixed and regression-tested before delivery.
