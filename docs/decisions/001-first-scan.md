# ADR-001: First-scan contract

**Status:** Accepted
**Decided by:** USER (scope) and AGENT (implementation choices below)
**Date:** 2026-11-17
**Feature:** first-scan

## USER decisions

Product prose: “The utility should be written in Python.” “The utility should be a CLI
that can run under a Linux-like shell environment.” Binary content defines duplicates;
first version inventories recursively without changing files.

SURVEY answers:
- “Only media files selected by an extension list”
- “JSON with root-relative paths, group sizes, and errors; suitable for future tooling (Recommended)”
- “Skip symbolic links; list hard-linked paths together and identify shared storage (Recommended)”

## AGENT decisions and alternatives

Use standard-library Python 3.11+ on POSIX, one root per invocation, `python3 -m
 dup_media ROOT`. No installation dependency. SQLite temporary storage bounds index
memory; sequential size filtering, SHA-256 candidate hashing, then streaming byte
comparison avoid treating a digest as proof. Full hashing of every file wastes I/O
on unique sizes. A database is preferable to a memory-only index for unknown counts.

Default extensions cover common image/audio/video formats and can be overridden with
`--extensions jpg,png,...`. Extension selection is case-insensitive, not media decoding.
Skip all symlinks and special files. Include empty media files. Hardlinks remain paths
in groups, annotated with a per-scan storage identity; do not claim reclaimable bytes.

JSON goes to stdout; diagnostics contain relative paths and stable error codes, never
raw OS exception text. Exit 0 complete, 1 incomplete, 2 invalid invocation/root, 130
cancelled. Cancellation emits no completed inventory. Scratch files use system temp;
refuse a root containing that scratch location. Shell redirection is the caller's
responsibility: inventory output must be outside the scan tree.

No snapshot isolation is possible on a live filesystem. Check device/inode/size/mtime/
ctime before and after reads and revalidate reported members; report detected changes
as errors. A later modification can still invalidate an inventory. No move/delete
operations may trust it without fresh validation.
