# ADR-004: macOS data-stream relocation

Status: Accepted. Date: 2026-11-18. Supersedes ADR-003 strict metadata requirement only on macOS.

USER: “Can I run it on macOS? ... I am willing to relax the preservation of metadata such as time and permission.” Then “OK. please proceed with the support of macOS”. Clarification: “Reject resource forks; allow other metadata loss (Recommended)”.

AGENT: support 64-bit macOS APFS under ordinary user permissions. Preserve and verify exact main-stream bytes; do not copy mode, times, ownership, ACLs, tags or xattrs. Create copies mode0600 (subject to inherited ACLs), directories0700. Reject any resource-fork attribute on keeper/victim/copy, including empty ones, and conservatively reject file flags. Always report `macos-data-only` policy; no silent strict-preservation claim. Existing Linux strict policy remains.

Use descriptor physical paths (F_GETPATH_NOFIRMLINK) for overlap/scratch/mount safety and path-pinned SQLite journal with FULL synchronous/fullfsync. Keep exclusive namespace requirement. Full-sync copied files before publication; directory fsync remains mandatory. Reject unsupported filesystems; no HFS+/SMB/exFAT/NAS claim.

Alternative strict copyfile metadata preservation requires broader platform contracts and conflicts with owner's accepted simplification. Merely bypassing Linux gates loses containment/journal guarantees. Revisit for additional filesystems or metadata preservation. No automatic recovery or hardware power-loss certification. No merge or private-media operation authority.
