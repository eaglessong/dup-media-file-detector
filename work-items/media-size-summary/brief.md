# Media size summary

**Status:** Implemented, locally verified and agent-reviewed — PR delivery pending

## Problem and intended user

The owner wants to know the total size of all media files under the scanned folder,
including its nested subfolders. The current duplicate inventory does not provide
this overall media-size summary.

## Desired behavior with examples

Report the total size of all media files selected by the scan, including files that
have no duplicate. For example, selected media files of 100, 100, and 50 bytes yield
250 bytes when counting each file path; non-media files do not contribute.

USER confirmed per-path logical-byte counting including hardlinks, an always-present
JSON summary of bytes and media file count, and clearly marked partial totals for
successfully validated files when the scan is incomplete. See the
[design](../../docs/design/media-size-summary.md) and
[attributed decisions](../../docs/decisions/002-media-size-summary.md).

## Acceptance criteria

- R1 (USER goal): Report the total size of all media files under the scanned folder.
- R2 (consistent selection): Apply the scan's recursive media-selection policy consistently,
  including unique files as well as duplicate files.
- R3 (existing safety constraint): Keep scanning read-only and preserve originals.

## Constraints and non-goals

- USER subsequently authorized implementation with `/forge implement media-size-summary`.
- Retain the project's Python CLI, local processing, and original-file safety constraints.
- File deletion, moves, uploads, and perceptual similarity are outside this work item's goal.

## SURVEY outcome and next step

All three consequential questions resolved by the USER on 2026-11-18: logical bytes
per selected path including hardlinks; always-on JSON bytes/count; partial validated
results with incomplete status/errors retained. Exact answers are in ADR-002.

The design defines R1–R6, interfaces, failure semantics and planned acceptance tests.
Field names and schema compatibility are explicit AGENT proposals. The initial design delivery changed no application code or tests. Implementation is
now authorized; requirements and decisions remain unchanged.
