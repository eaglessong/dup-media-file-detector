# ADR-002: Whole-scan media size summary

**Status:** Accepted — implemented
**Decided by:** USER (behavior) and AGENT (technical proposal, identified below)
**Date:** 2026-11-18
**Feature:** media-size-summary

## Context and options

The first scan indexes selected media paths/sizes but reports only duplicate groups.
Adding group totals would omit unique media. Logical bytes per path, bytes per unique
inode, and allocated storage measure different things. Output can extend the existing
JSON, require a flag, or use a separate size-only command. Incomplete scans can report
validated observations or suppress totals. See the [design](../design/media-size-summary.md).

## Decision and rationale

USER goal: “reporting the total size of all media files under the scanned folder.”
The initial USER request was design only. The later USER request,
“/forge implement media-size-summary”, authorizes implementing this design.

Actual SURVEY answers on 2026-11-18:

- “Count logical bytes per selected path, including each hardlink (Recommended)”
- “Always add total bytes and media file count to the existing JSON report (Recommended)”
- “Show a clearly marked partial total for successfully validated files; keep the incomplete status and errors (Recommended)”

AGENT technical proposal: add `summary` to existing schema-version-1 JSON, containing
`media_file_count`, `total_size_bytes`, and `complete`. Use exact nonnegative integer
bytes, no formatted-unit string. Accumulate indexed sizes for `valid=1` rows after
final validation with Python integers and streaming row iteration. Do not query only
duplicate candidates, use floating-point totals, or use SQLite SUM for potentially
overflowing aggregate integers. `summary.complete` equals report `complete`.

This reuses existing selection, safety and errors; it adds no scan pass, flags, content
reads, media decoder, external dependency, or physical-storage claim. A schema-version
bump is an alternative if strict consumer compatibility requires one during resumption.

## Rollback or reversibility

The initial delivery changed planning documents only. Implementation is now authorized;
revise this ADR/design if requirements change. Once implemented, removing/renaming the public summary is an
output-contract change requiring a new compatibility decision. No source-file mutation
is authorized.

## Consequences and revisit trigger

Hardlinks and separate byte-identical copies both contribute once per selected path.
Sparse files contribute logical length. Incomplete totals exclude invalidated files but
can omit unknown paths; they are observations, not allocated/reclaimable disk space or
a guaranteed lower bound for a changing tree. No output is promised after cancellation
or fatal errors. Strict JSON consumers may need to allow the additive field. Revisit
for a requested size-only mode, physical-storage metrics, schema changes, or a stronger
snapshot requirement. Agent-chosen field names/compatibility choices remain reviewable.
