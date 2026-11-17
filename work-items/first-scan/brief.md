# First read-only duplicate scan

**Status:** Draft — proposed first feature

## Problem and intended user

A person wants to find duplicate files in a local media collection without risking
the originals. Confirm the user's preferred interface and platform before building.

## Desired behavior with examples

Proposed: given two selected folders containing two identical media files and one
different file, report exactly one duplicate group and leave all three files unchanged.
Report read failures clearly. Exact equality and perceptual similarity are distinct.

## Acceptance criteria

Proposed requirements R1–R5 and the verification matrix are in
`docs/design/first-scan.md`; confirm them during SURVEY.

## Constraints and non-goals

Proposed: local, read-only, no uploads, no automatic deletion/moves, exact duplicates
first. These are agent suggestions, not product-owner decisions.

## Open questions

Resolve `docs/PRODUCT.md`: OS, UI, language/distribution, media types, expected scale,
link handling, result format, and duplicate-proof policy. Then revise the design before
implementation. No application feature has been implemented or verified yet.
