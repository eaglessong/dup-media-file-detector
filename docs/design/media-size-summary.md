# Media size summary

**Status:** Implemented, locally verified and agent-reviewed — PR delivery pending
**Date:** 2026-11-18
**Requirements:** [brief](../../work-items/media-size-summary/brief.md)
**Decisions:** [ADR-002](../decisions/002-media-size-summary.md)

## Problem and current state

Baseline receipts below refer to pre-feature commit 59f05d4. Implementation verification
and current line references are recorded in the evidence.

The owner needs the total size of all selected media under a recursively scanned folder,
including unique media. The existing CLI calls `Scan.run()` then `Scan.write()`
(`dup_media/__main__.py:22–24`). Selected regular paths and stat sizes enter SQLite
`files` during enumeration (`dup_media/scan.py:138–140`). Errors can invalidate rows;
final validation checks every remaining valid row (`:184–187`, `:237–255`). Output
currently has schema_version, complete, groups and errors; group total_bytes includes
only duplicate members (`:257–277`). Summing group totals cannot satisfy this goal.

The existing Python 3.11+/POSIX/SQLite implementation, extension list/override, read-only
contract and exact byte comparison remain the foundation. This document proposes future
behavior; implementation follows this contract.

## Requirements and non-goals

- **R1 — Whole selection:** Include all successfully validated selected regular media
  paths under the root recursively, whether unique, duplicated or hard-linked. Count
  each selected path once and sum its logical `st_size` in bytes. Hardlinks count per
  path; sparse-file holes still count toward logical size.
- **R2 — Output:** Every successfully serialized scan report includes a `summary` object
  with integer `media_file_count`, integer `total_size_bytes`, and boolean `complete`.
  Integers are exact and nonnegative. Preserve existing duplicate groups and their
  field meanings. A complete empty/no-matching-media tree yields count 0, bytes 0.
- **R3 — Selection consistency:** Use existing case-insensitive extension selection and
  `--extensions` override. Empty selected files count as files and contribute zero bytes.
  Ignore nonselected extensions, all symlinks, and special files. Directories themselves
  never contribute bytes; keep existing alias/encoding/error handling.
- **R4 — Partial results:** After all current file/directory validation, aggregate only
  indexed `valid=1` files. An error anywhere keeps report and summary complete false,
  preserves existing error records and exit 1, and labels totals partial through that
  boolean. Files invalidated at any earlier stage stay excluded even if accessible later.
- **R5 — File safety and lifecycle:** Keep originals, containment, metadata checks,
  diagnostics/privacy and exits unchanged. Invalid invocation/root or fatal scan/storage
  failure remains exit 2 without a usable report; SIGINT remains 130. Any partial output
  after cancellation/fatal serialization failure must be discarded.
- **R6 — Resource behavior:** Reuse the disk index with streaming integer aggregation;
  no additional filesystem traversal, source-content reads, or file-count-sized memory
  list. Do not derive the total solely from hash candidates or duplicate-group membership.

R1/per-path counting, R2/always-on bytes+count, and R4/partial totals implement explicit
USER choices in ADR-002. Field names, integer-only display, schema compatibility and
aggregation details are AGENT proposals. Existing safety constraints remain applicable.

Non-goals: size-only command, new CLI switches, formatted units, allocated/reclaimable
space, per-extension/per-directory subtotals, progress, resume, media decoding, modified
matching proof, moves/deletions, uploads, and a new platform-support claim.

## Alternatives and recommendation

1. **Sum duplicate group totals:** smallest output-only change but misses unique files;
   rejected because it fails R1.
2. **Accumulate during traversal:** small overhead but a plain running sum includes
   later-invalidated paths. Correcting it adds bookkeeping and mutation/error complexity.
3. **Aggregate the validated SQLite file index (recommended):** one sequential index
   query, consistent with validation and existing disk-backed state. Increment Python
   integers to avoid SQLite aggregate integer overflow or floating-point rounding.
4. **Separate size-only command:** can avoid duplicate matching time but adds a new
   command/lifecycle and was not selected by the owner. Defer to a separate request.

## Architecture and interfaces

The user entry point stays `python3 -m dup_media ROOT [--extensions jpg,png,...]`.

Proposed data flow:

1. Existing enumeration records selected paths and sizes.
2. Existing hashing/byte comparison and error handling run unchanged.
3. Existing final file/directory revalidation completes and commits the index.
4. A private summary helper iterates `SELECT size FROM files WHERE valid=1`, counts
   rows, and sums sizes using Python integers. Do not filter by digest/group_id or
   DISTINCT device/inode. No SQLite `SUM` or `TOTAL` is used.
5. `Scan.write()` computes the summary before emitting JSON, obtains completeness using
   the same error-table check as the top-level report, and writes the new object with
   the existing streamed groups/errors. Use one shared completeness value.

Example report for validated paths of 100, 100, and 50 bytes (first two
byte-identical), using abbreviated paths in this illustrative JSON:

```json
{
  "schema_version": 1,
  "complete": true,
  "summary": {
    "media_file_count": 3,
    "total_size_bytes": 250,
    "complete": true
  },
  "groups": [{
    "size_bytes": 100,
    "total_bytes": 200,
    "files": [
      {"path": "a.jpg", "storage_id": "1:10"},
      {"path": "nested/b.jpg", "storage_id": "1:11"}
    ]
  }],
  "errors": []
}
```

If the unique 50-byte path becomes invalid, emit summary count 2, bytes 200, complete
false; report complete false, the existing relative-path error and exit 1. If all
selected paths are invalid, emit zero/zero with complete false. An unreadable directory
can hide an unknown number of files; never infer its count/size or present partial
observations as the full tree. Bytes are not a guaranteed lower bound for a live tree.

Implementation targets:

| Target | Planned responsibility |
| --- | --- |
| dup_media/scan.py | Private streamed aggregation helper and additive summary serialization after validation |
| tests/integration/test_scan.py | Real-tree selection, totals, hardlinks, zero cases, mutation/permissions and preservation assertions |
| tests/e2e/test_cli.py | Actual module CLI JSON/exit/partial-summary regression assertions |
| tests/test_application.py | Arithmetic-boundary helper test if useful; do not call it filesystem proof |
| README.md / CONTRIBUTING.md | Field semantics, partial status, logical bytes and examples |

No dependency, persistent database migration, CLI argument, or new traversal is planned.

## File safety and privacy

Reuse no-follow descriptor-relative opens, root and scratch restrictions, file identity/
stability checks, and final revalidation. Totals reflect validated indexed sizes, not
new reads of originals. OS read-atime effects remain as documented by first-scan.
No extra source paths/content are logged; summary exposes only aggregate integers and
status. Keep inventory redirection outside the selected root. A live filesystem can
change after validation; a quiet tree/snapshot is needed for point-in-time consistency.
The report grants no authority for future deletion or moves.

## Scale and operations

The owner described potentially hundreds of GB with no scan-time limit; no representative
file count, NAS benchmark or throughput measurement exists for this feature. The new
work is O(N) row visits for N valid selected paths, constant extra row storage plus
integer accumulators (whose bit length grows with the total), and a constant-size JSON
object. Index size and existing hashing/comparison I/O remain the scanner's baseline.
Count/sum all rows, including huge individual logical file sizes and hardlinks; do not
materialize paths/groups for the summary. Keep SIGINT responsive during aggregation.

Future bounded scale check: generate 10,000 tiny selected files with a known sum, record
wall time, peak memory and scratch size for a defined environment, and compare baseline
versus summary-enabled code. This is a measurement plan, not a performance promise or
an acceptance threshold. Synology remains an unavailable hardware validation target.

## Diagnostics and user-visible outcomes

| Condition | Summary | Existing report/exit |
| --- | --- | --- |
| All requested traversal/validation succeeds | Exact observed count/bytes, complete true | complete true; errors []; exit 0 |
| Empty tree or no selected extensions | 0 files, 0 bytes, complete true | exit 0 |
| Any recoverable scan error, including duplicate read failure | Valid subset count/bytes, complete false | relative errors retained; complete false; exit 1 |
| Invalid invocation/root or fatal I/O/SQLite error | No usable report promised | generic diagnostics; exit 2 |
| SIGINT, including during aggregation | No usable report promised; discard partial output | cancellation diagnostic; exit 130 |

No new normal stderr messages, progress output or separate human-readable total.

## Verification and acceptance matrix

The matrix below defines acceptance. Tests now implement these cases; actual run
results, limits, and coverage receipts are recorded in the feature evidence. Shared
fixtures carry explicit expected totals across integration/CLI tests.

| Requirement | Integration test | Entry-point E2E test | Demo outcome |
| --- | --- | --- | --- |
| R1/R2 | Temporary files 100/100/50 bytes; first pair equal; assert count 3, total 250 and old group 200 | Real `python3 -m dup_media ROOT`; assert summary and group fields, exit 0 | Whole total includes unique media |
| R1/R3 | Hardlink the 100-byte original; assert count 4, total 350, shared storage identity retained | Same fixture through CLI; assert count 4/350 | Hardlinks counted per path |
| R2/R3 | Empty tree; ignored-only tree; two empty selected files => counts 0, 0, 2 and bytes all 0 | Assert 0/0 complete vs 2/0 complete | Zero bytes differs from zero files |
| R3 | Nested Unicode/uppercase paths, override extensions, symlinks inside/outside/loop, FIFO | Expected count/sum under default and override; outside content excluded | Exactly the scan's selection policy |
| R4 | Mutate a selected file on real filesystem after enumeration before validation; check invalidated row excluded, errors retained | Real mode-restricted file/directory under non-root; known readable subset summed; exit 1 and both complete flags false | Clearly partial result |
| R4 | All files invalidated; error-only unreadable directory; late directory addition | Assert subset/zero totals with complete false, never empty-success | Unknown files not guessed |
| R5 | Compare names/bytes before/after success, mutation-induced scan failure excluding deliberate fixture mutation from preservation oracle | Preserve originals on success and actual permission-error scan; existing root validation/SIGINT tests | Read-only and original exits retained |
| R6 | Sparse unique-size files above 4 GiB; known logical sum, no content hashing for unique sizes; inspect helper for streaming | CLI asserts exact integer total; SIGINT still works on sparse candidate fixture | Logical size independent of allocated blocks |
| R6 | Arithmetic test of synthetic indexed rows with total above signed 64-bit, clearly labeled index/arithmetic test | No huge-tree CLI claim; sparse CLI case above covers shipped integer output | No aggregate overflow/rounding |

Test-data verdict **ADEQUATE for design feasibility**: temporary synthetic byte files,
real hardlinks/symlinks/FIFO/chmod and controlled real mutations are feasible using the
existing fixture approach. No media decoding or third-party media is needed. Sparse
cases require filesystem support; permission cases require non-root. Existing Linux
Python 3.11/3.13 CI is the planned environment for Linux filename and permission behavior.
Missing preconditions must be explicit skips/gaps and closed in supported-platform CI
before implementation completion. Summary-specific integration and CLI tests must pass before completion.

Capture gate: no external API, decoder or new-platform claim. The JSON extension is
specified here and can use synthetic expected output; no private/live capture needed.
When implementing, record recipes in tests/fixtures/README.md and run the actual syntax,
application contract, filesystem and CLI commands from CONTRIBUTING.md plus framework
validation. Assert exact counts/bytes, not merely presence of the new key.

## Delivery and rollout

The initial delivery stopped at design-delivered. The USER subsequently authorized
implementation, which retains the Python/runtime/entry-point setup.
Propose an additive `summary` field while retaining schema_version 1 and all old fields;
lenient existing consumers remain compatible. Strict consumers that reject unknown
fields must be updated; if one is identified, revisit versioning before implementation.
No external consumer inventory was available, so strict-consumer compatibility is an
explicit risk, not a verified guarantee. No persistent data migration or recovery step.
Do not publish README output as shipped until implemented and verified. Implementation delivery includes a forge PR and CI verification; merge requires
separate current user authority.

## Decision records

- [ADR-001](../decisions/001-first-scan.md): accepted selection/safety/CLI baseline.
- [ADR-002](../decisions/002-media-size-summary.md): actual USER answers and separately
  attributed AGENT schema, field-name, arithmetic and integration proposals.

## Open questions and risks

No consequential USER question remains after SURVEY. Revisit if implementation discovers
a strict schema consumer, invalid assumptions about validation, or a required environment
that cannot exercise acceptance. Incomplete totals exclude invalidated rows and unknown
paths; duplication-stage errors may also exclude a file with known metadata. Total logical
bytes do not mean unique content, disk allocation or recoverable space. Existing live-tree
consistency and unavailable NAS/production-scale validation limits remain.

## Implementation resumption — 2026-11-18

USER requested `/forge implement media-size-summary`. Re-entered SMELT and confirmed
R1–R6, prior SURVEY answers, and ADR-002 against unchanged scanner/base 59f05d4.
No material ambiguity or strict-schema consumer was found in the repository. Proceed
with the specified additive schema-version-1 summary. Earlier design-only statements
record the prior delivery boundary; this request now authorizes implementation/tests
and a forge PR, not merging. Existing Linux CI discovery commands cover new test files.
