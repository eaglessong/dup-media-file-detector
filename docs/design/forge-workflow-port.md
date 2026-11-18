# Full forge workflow adaptation

**Status:** Implemented — ready for owner review

## Problem and current state

The existing forge entry points are a short router to docs/WORKFLOW.md. They lack the
source workflow's concrete role prompts, phase prerequisites and supporting protocols.
The project now has a Python/POSIX/SQLite media CLI and a standalone code_review skill.

## Requirements and non-goals

- R1: Preserve PROSPECT, SURVEY, SMELT, FORGE, TEMPER, ASSAY and STAMP with explicit
  entry/exit evidence, risk-sized execution, autonomy boundaries and resumable artifacts.
- R2: Adapt all five reconnaissance and four ASSAY prompts with explicit bound inputs,
  distinct instruments, receipts, honest uncertainty and no recursive delegation.
- R3: Supply applicable decision, test-data, capture, shortcut-resistance and knowledge-map
  references plus a shared prompt/evidence contract.
- R4: Integrate code_review into ASSAY without recursively invoking forge or duplicating
  a second full panel. Supply test-realism verdicts and scoped scale/security audits.
- R5: Keep Codex/Claude entry points identical, validate prompt/resource completeness and
  binding before dispatch, and add tests proving broken inputs/resources fail validation.
- R6: Do not import internal services, production assumptions, merge authority, or a
  deployment stack. Preserve the current application's supported contracts and user choices.

## Alternatives and recommendation

Keeping the short router does not satisfy the requested port. Copying the source unchanged
requires unavailable services and inappropriate production topology. Use a concise skill
router, a detailed canonical workflow, shared repo-root docs/forge/prompts and references,
and standard-library prompt rendering/structural checks. Shared materials avoid divergent
copies between Codex and Claude. No dependency or hosted agent service is added. Design-only handoff has an explicit
design-delivered state, separate from application completion; rendered template links
are resolved to the target checkout so scratch-file location does not break them.

## Architecture and interfaces

Both skill entry points route to docs/WORKFLOW.md and its prompt/protocol references.
LIGHT combines reconnaissance instruments in one role pass plus a premise challenge;
FULL separates five scouts. ASSAY uses code_review as its synthesis and adversarial process,
feeding applicable forge seat reports rather than launching a duplicate panel. In clients
without delegation, perform explicitly labelled sequential role passes. The rendering CLI
binds role-specific JSON context into prompts, refusing missing/unknown/empty inputs and
unexpanded placeholders before dispatch; render output is data, never shell commands.

## Safety and privacy

Scouts/reviewers read only and do not execute candidate code or tests. The coordinating
agent owns safe fixture generation, tests and bounded synthetic benchmarks. Never use
personal media as test input or capture private paths/content into Git. Capture is conditional
on a real external-format/platform boundary; local synthetic exact-byte tests need no live
API. Missing required evidence blocks the affected completion claim, not unrelated work.
No automatic merges, releases, cloud access, paid runs or external posting grants.

## Scale and operations

Project-size risk tracks avoid mandatory large fan-out on every change. Measure local
workloads only with disposable data and explicit limits; never claim NAS production
performance from a laptop. Read targeted files and return receipts, not source dumps.

## Verification matrix

| Requirement | Verification |
| --- | --- |
| R1/R3/R6 | Review canonical phases/protocols and scoped source adaptation |
| R2/R5 | Renderer round-trip and missing/unknown/unbound input tests; missing material and mirror drift tests |
| R4 | Review integration contract and independent workflow forward-test |
| All | Existing framework tests, skill validation, GitHub CI, isolated behavioral evaluation |

## Decisions

USER: “If possible, I would like to port the key phases of the /forge workflow as well
as the applicable prompts with its supporting materials.”
AGENT: use shared materials, sequential fallback, conditional captures, scoped local
workloads and existing review synthesis. Do not copy company infrastructure or unsupported
service assumptions. Existing attribution and media safety constraints remain authoritative.

## Delivery

Open a PR with evidence and evaluation limits; verify CI and leave it unmerged. Client
slash-command discovery and fully autonomous end-to-end feature execution cannot be
proved by structural tests and must not be claimed.
