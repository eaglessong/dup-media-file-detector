# ADR-005: Read-only mutation-permission preflight

Status: Accepted. Date:2026-11-18. Decision-maker: AGENT.

Context: PR8 review5951648652 found missing static permission checks, contrary to
existing source-removal/global-preflight design. USER requests `/forge follow up PR #8`.
This record implements that existing contract; no new USER metadata preference inferred.

Use descriptor-relative Darwin faccessat AT_EACCESS|AT_SYMLINK_NOFOLLOW with extended
_DELETE_OK, _WRITE_OK, _APPEND_OK, _RMFILE_OK and _EXECUTE_OK actions as applicable.
Native authorization handles ACL/sticky semantics; do not infer permissions solely from
mode bits or write probe files. Linux retains existing privileged adapter and effective
access checks. Check every planned source/destination and the journal creation parent
before mutation; ordinary scans unchanged. Recheck actual mutations as before.

Reject file/directory-inheritable ACLs on creation parents conservatively because current
ancestor access cannot prove permissions of future descendants/staging files. Permit
non-inheritable ACLs when native authorization succeeds. This narrows accepted creation
layouts explicitly; alternative inheritance emulation is broader and error-prone, and
write probes violate dry-run. Stable relative errors disclose the blocked capability.
No guarantee against later permission changes or arbitrary concurrent writers. Revisit
for native inheritance modeling, additional filesystems or concurrent operation support.


## Linux parent-inode follow-up (2026-11-18, AGENT)

PR8 review5951891667 established that W/X authorization does not imply unlink is
allowed in an append-only ext4 directory. Read FS_IOC_GETFLAGS on every source-removal
parent; reject APPEND and IMMUTABLE before mutation. For destination/journal creation
parents, accept only ordinary EXTENTS/INDEX directory layout flags and zero project
policy (FS_IOC_FSGETXATTR; allocated extent count is not policy). Reject other flags or
project inheritance conservatively: staging metadata and SQLite journal cleanup cannot
be proven compatible without mutation. Check the nearest existing creation ancestor
when descendants are absent. Do not clear flags or create probe files in product code.
This implements the existing whole-plan contract; no new USER preference is inferred.
Tests use disposable native ext4 flags/project-ID controls, later-group ordering and
whole-namespace snapshots in integration and shipped CLI tiers. Source-parent harmless
flags need not be rejected because deletion does not inherit them. Ordinary scanning
and the Darwin adapter keep their current contracts.
