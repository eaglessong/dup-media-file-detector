# {title}

**Status:** Proposed

## Problem and current state

Cite explored code or say the relevant component does not exist.

## Requirements and non-goals

Number observable requirements R1, R2, … and identify scope boundaries.

## Alternatives and recommendation

Compare realistic options, tradeoffs, and why the chosen option meets the requirements.

## Architecture and interfaces

Describe user entry point, data flow, dependencies, and output/error contracts.

## File safety and privacy

Address root boundaries, symlinks, file changes during a scan, read-only behavior,
private paths, and recovery if a separately authorized operation modifies files.

## Scale and operations

State expected workload, memory/I/O bounds, cancellation, diagnostics, and assumptions.

## Diagnostics and user-visible outcomes

Define complete/incomplete/error/cancel behavior, stdout/stderr or report contracts,
and useful diagnostics without unnecessary private content. Do not invent a cloud
telemetry dependency for a local feature.

## Verification and acceptance matrix

| Requirement | Integration test | Entry-point E2E test | Demo outcome |
| --- | --- | --- | --- |
| R1 | Planned | Planned | Planned |

State fixture provenance, required environment/preconditions, any capture trigger and
ADEQUATE/PARTIAL/BLOCKED verdict. Application features need integration plus actual
entry-point E2E behavior; tooling/docs use their scoped structural and instruction checks.

## Delivery and rollout

Document install/run path, compatibility, CI checks, and any migration/recovery plan.

## Decision records

For each consequential decision use `docs/templates/adr.md`. Mark agent assumptions
AGENT; USER decisions require actual user input. Link records in `docs/decisions/`.

## Open questions and risks

Resolve material questions before implementation; record limitations explicitly.
