# Move duplicate media files

**Status:** Implemented, verified and agent-reviewed — PR #8 remains unmerged

## Goal and user requirements

USER requested a work item named `move-dup-files` and its related design, explicitly:
“Do not implement.” The desired future feature will:

- Keep exactly one selected source path in each exact duplicate media group.
- Relocate the other duplicate paths to a root folder supplied on the command line.
- Bail out without proceeding if that destination is under the scanned source root.
- Preserve each moved file's source-relative directory structure under the destination.
- Offer dry-run mode without actually moving files.

Example: with byte-identical `a.jpg` and `nested/b.jpg`, choosing `a.jpg` as keeper
would relocate `nested/b.jpg` to `DEST/nested/b.jpg`. This illustrates mapping only;
USER chose the first root-relative path in deterministic alphabetical order.

## Existing constraints and scope

Retain extension selection, exact byte proof, skipped symlinks/special files and the
existing read-only scan command. Only a future explicit relocation invocation may
modify source paths. Unique media and non-media remain untouched. No deletion-only,
approximate matching, uploads or media decoding. USER subsequently authorized implementation
with `/forge implement move-dup-files`; no merge or real-library operation is requested.

## SURVEY decisions

USER chose deterministic alphabetical keeper selection; cross-volume copy, verify, then
remove; a fresh scan for each run; and strict preservation of bytes/permissions/mtime
with rejection when attached metadata cannot be preserved. Exact answers are recorded
in [ADR-003](../../docs/decisions/003-move-dup-files.md). Additional safety defaults and
mechanisms are explicitly AGENT choices in the design/ADR. No material USER question
remains; filesystem capability probes are future implementation prerequisites.

## Acceptance outline

1. Successful relocation leaves one keeper path per selected exact group.
2. Every removed duplicate source path has an equal-byte destination at the same
   relative path; unique/unselected paths are preserved.
3. Invalid overlapping roots fail before traversal or destination changes.
4. Dry-run returns an inspectable keeper/move plan without modifying either tree.
5. Destination conflicts never overwrite data; failures/cancellation preserve enough
   copies and durable evidence to recover honestly from partial completion.

See [design](../../docs/design/move-dup-files.md) and [evidence](evidence.md).
