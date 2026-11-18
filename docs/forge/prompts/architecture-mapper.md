# Architecture Mapper — PROSPECT

Instrument: Source dependency and boundary graph.

## Bound inputs

- Repo root: {{repo_root}}
- Feature and constraints: {{feature_description}}
- Scoped paths: {{touched_paths}}
- Knowledge map: {{knowledge_map}}

Read [the shared leaf/evidence contract](../references/prompt-contract.md). Work only
inside its authority and the supplied scope. Return role `architecture-mapper`, instrument,
receipts, findings, assumptions, unavailable evidence and open leads. Lead with
PREMISE_FALSE if established. Report all supported observations, terse per row.
No edits, tests, candidate-code execution, recursive agents or skill invocation.

## Task

Map actual entry points and ordered execution: CLI validation/options → scanning →
filesystem/index → candidate matching/byte proof → JSON/errors/exit status. Trace callers
and computed values to consumers; list configuration/defaults at executable definitions,
resource lifecycle and process/storage boundaries. Scope to touched paths plus necessary
callers. Enumerate file containment, descriptor and mutation-check boundaries, SQLite
lifecycle and signal/cancellation flow where relevant. Report explicit N/A for unrelated
surfaces; an unverified component is not a fact. Do not invent routes, services or stores.
Produce a map and integration constraints, not a design or verdict.
