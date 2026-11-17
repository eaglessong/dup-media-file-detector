# First read-only duplicate scan

**Status:** Proposed — starter example, not approved for implementation

## Problem and current state

The repository currently has an agent development framework and no media scanning
application. A user wants a useful first way to locate duplicate media safely.

## Proposed requirements and non-goals

- R1: Scan explicitly selected local directories using an agreed media-selection policy.
- R2: Report exact byte-duplicate groups deterministically; distinguish similar media.
- R3: Leave every source file's contents and name unchanged, including on failure.
- R4: Report unreadable/changed files and cancellation clearly; avoid silent success
  when the requested scan could not be completed.
- R5: Do not follow links outside selected roots or upload file content.

Proposed non-goals: deletion/moving, perceptual matching, cloud drives, and background
watching. These are AGENT proposals to confirm in SURVEY, not user requirements yet.

## Alternatives and recommendation

Compare a CLI, desktop app, and local web UI after confirming the owner's desired
experience. Compare full hashing of every file with size-first candidate grouping and
content verification. No language or UI is selected by this starter.

## Architecture and interfaces

Design the entry point, recursive enumeration policy, candidate grouping, duplicate
proof (including hash collision policy), mutation detection, and reporting contract.
Specify empty-file behavior, overlapping roots, symlinks/hardlinks, case sensitivity,
invalid paths, inaccessible files, and output ordering before implementation.

## File safety and privacy

Read-only is the default. Use temporary synthetic fixtures for tests. Do not log full
personal paths by default. Recheck file identity/stability across scan steps and define
what happens when a file changes. Treat approximate fingerprints as candidate hints.

## Scale and operations

Ask for representative file counts/bytes and storage type. Specify memory and open-file
bounds, concurrent I/O, progress, and cancellation; benchmark before claiming performance.

## Verification and acceptance matrix

| Requirement | Integration test | Entry-point E2E test | Demo outcome |
| --- | --- | --- | --- |
| R1/R2 | Duplicate/different bytes and agreed media filter | Real entry point on temporary tree | Exact expected groups |
| R3 | Compare names/bytes before and after success/failure | Verify input tree unchanged | Originals preserved |
| R4 | Errors, mutation race, cancellation | Agreed failure output/exit behavior | No false completion |
| R5 | Symlinks and root boundaries | Outside-root fixture excluded | Scan stays in scope |

## Delivery and rollout

First implementation must choose/document the stack, installation, run command, actual
application CI checks, and a user-friendly demo. No implementation exists yet.

## Decision records

Create ADRs after SURVEY. The product owner has not chosen a stack, UI, platform, or
matching algorithm. Read-only and exact-first are proposed starting constraints.

## Open questions and risks

Resolve the open questions in `docs/PRODUCT.md`, confirm proposed requirements above,
and define fixture coverage before writing application code.
