# macOS relocation support

Add normal-user macOS support to exact-duplicate relocation. Keep fresh proof, external destination, dry-run, no overwrite and durable journal safeguards. USER permits metadata loss on macOS, but explicitly requires rejection of resource forks. No real-library operation or merge is requested.

Scope: native 64-bit macOS/APFS, same and cross-volume copy/verify/remove; strict Linux adapter unchanged. See docs/design/macos-relocation.md and ADR-004.
