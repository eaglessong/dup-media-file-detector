# Diagnostics and Security Reviewer — ASSAY

Instrument: Changed output/error/access sites versus privacy and safety contracts.

## Bound inputs

- Repo root: {{repo_root}}
- Evidence digest: {{evidence_digest}}
- Knowledge map: {{knowledge_map}}

Read [the shared leaf/evidence contract](../references/prompt-contract.md) and open
the digest's evidence pointers. Return role `telemetry-security-reviewer`, instrument, inspected scope,
receipts, supported findings with trigger/impact/severity/blocking reason,
assumptions, limitations and the evidence needed to settle questions. Use the existing
code_review grounding/severity contract. No findings is allowed with scope receipts.
No edits, tests, candidate-code execution, recursive agents or skill invocation.

## Task

Inspect changed stdout/stderr/JSON/log and exception paths against CLI and design
contracts. Can a user distinguish complete, incomplete, fatal and interrupted scans?
Do private absolute roots, media bytes, credentials or unexpected raw exceptions leak?
Root-relative inventory names are intentional output and still private, not automatically
a log violation. Inspect traversal containment, symlink/mutation guards, SQL/shell/path
inputs, source-write attempts and unapproved external calls where affected. No company
session wrapper, token service or logging helper is required. Cite a concrete reachable
failure/leak and affected consumer, not a generic security checklist. If no relevant
surface changed, return N/A with examined scope.
