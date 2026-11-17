# First read-only duplicate scan

**Status:** Implemented, verified and self-reviewed; ready for owner PR review

## Current state and requirements

Framework only; Python POSIX CLI for a Synology owner's recursive media inventory.
[Decisions](../decisions/001-first-scan.md) separate USER answers and AGENT choices.

- R1: Recursively scan one directory, selecting common media extensions, configurable
  by `--extensions`. Match case-insensitively; include zero-byte files.
- R2: Deterministic exact groups: size + SHA-256 candidates, byte comparison proof;
  relative paths, size, group total bytes, and per-path shared-storage identity.
- R3: Never write, rename, delete, upload, or intentionally change source metadata.
  OS read access time updates may occur. No symlink traversal, including root ancestors.
- R4: Relative-path error records and incomplete status for read/permission/change
  failures. SIGINT exit 130; invalid arguments/root exit 2; incomplete exit 1.
- R5: Disk-backed index, sequential 1 MiB reads, bounded open files, deterministic
  output; preserve hard-linked paths and identify shared storage.

Non-goals: similarity, media decoding, destructive operations, resume, multi-root scans.

## Interfaces and data flow

`python3 -m dup_media ROOT [--extensions jpg,png,...] > /outside/root/inventory.json`

Open root and every ancestor without following symlinks. Enumerate with directory FDs,
detect repeated directory identities (report `directory_alias` rather than traverse cycles),
record selected regular files in temporary SQLite, group by size, hash candidates,
then partition equal digests by byte comparison. Every reopen walks from the held root
FD using O_NOFOLLOW for every component; verify regular type and recorded metadata.
Reject root paths containing `..`. Non-UTF-8 filenames are skipped with an escaped
`unsupported_filename_encoding` error and incomplete status. Final validation excludes changed members; groups with fewer than two members vanish.
JSON schema_version=1, complete boolean, groups array, errors array. Each group has
size_bytes, total_bytes, files [{path, storage_id}]; storage_id is device:inode text.
Groups and paths are sorted. Errors carry path and code. Paths use JSON escaping.
Stream groups and errors from disk to keep memory independent of total file count.
Scratch database is outside selected root. A directory move during traversal can
invalidate a live-tree view; safety checks catch observable identity changes, but a
snapshot is required for a point-in-time guarantee. Reads never mutate originals.

## Alternatives, scale, and rollout

See ADR-001: SQLite rather than all-path memory lists; size filtering rather than full
hashing; byte proof rather than trusting hashes. Sequential I/O suits NAS storage.
No throughput claim; hundreds of GB is an intended workload, not tested hardware.
Default extension list and runtime requirement documented in README. Linux CI required;
Synology hardware unavailable. Stdlib has no separate build/type/formatter dependency;
compile and CLI contract checks plus behavioral tests are application quality checks.

## Verification matrix

| Requirement | Integration | Entry-point E2E | Demo |
| --- | --- | --- | --- |
| R1/R2 | nested, Unicode, empty, extension override, forced hash collisions | module CLI JSON expected groups | two equal media files grouped |
| R3 | bytes/names unchanged after scan, outside symlink excluded | before/after tree comparison | originals intact |
| R4 | injected read errors and mutation; real permissions when available | invalid root, SIGINT, incomplete errors | explicit status/exit |
| R5 | hardlinks, special files, deterministic order | repeated output equal | shared storage shown |

## Risks and open questions

No consequential product questions remain. Source access time can change through OS
reads. Live-tree results are observations, not a deletion authorization. Permission
checks under root may require skipping a test with an explicit reason. PR delivery
requires working GitHub authentication. Review will be an explicitly labeled self-review.
