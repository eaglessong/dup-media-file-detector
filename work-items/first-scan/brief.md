# First read-only duplicate scan

**Status:** SURVEY resolved; implementation authorized

A Synology NAS owner needs a Python CLI to inventory exact binary duplicates under
one folder and its nested subfolders, potentially hundreds of GB, without modifying
originals. Scan time is unrestricted. Future operations may consume the inventory;
this feature performs no moves or deletions.

USER selected media-extension filtering, JSON with relative paths/group sizes/errors,
and skipping symlinks while including hard-linked paths with shared storage identified.
Requirements R1–R5 and acceptance mapping: [design](../../docs/design/first-scan.md).
Implementation defaults and actual USER quotes: [ADR](../../docs/decisions/001-first-scan.md).
No open consequential product questions remain.
