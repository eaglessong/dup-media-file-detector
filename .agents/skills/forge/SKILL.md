---
name: forge
description: Build a feature from a brief or design through reconnaissance, clarification, attributed design decisions, implementation, integration and entry-point testing, adversarial review, and a GitHub PR. Use for feature implementation or a scoped development wave; not standalone review or investigation.
---

# Forge — artifact-driven development

Read the repository-root `AGENTS.md`, `docs/PRODUCT.md`, contribution guidance and the
[canonical phase workflow](../../../docs/WORKFLOW.md). Resolve repo-root paths against
the target checkout. The workflow contains the phase prerequisites, LIGHT/FULL routing,
leaf-role prompts, test gates and PR delivery contract; follow the applicable phases,
not merely this summary. Respect an explicitly narrower user request such as design only.

Take the user's argument as a feature description, brief/design path, or wave. Scaffold
missing artifacts with `python3 scripts/forge.py new-feature <slug>`, preserving existing
designs. PROSPECT explores before SURVEY asks consequential questions. SMELT completes
the design and attributed decisions before FORGE implements. TEMPER proves changed
behavior through scoped integration and real user-entry-point tests. ASSAY combines
forge audits with code-review synthesis; STAMP delivers evidence and verifies GitHub CI.

Read supporting materials when their phase needs them:

- Before dispatch: [prompt/evidence contract](../../../docs/forge/references/prompt-contract.md)
  and [project knowledge map](../../../docs/forge/references/knowledge-map.md).
- During reconnaissance: [test-data protocol](../../../docs/forge/references/test-data-protocol.md).
- Before design/decision changes: [decision records](../../../docs/forge/references/decision-records.md).
- When a parser/platform/external-format boundary changes:
  [capture protocol](../../../docs/forge/references/live-capture-protocol.md).
- When scope/time compromises arise:
  [shortcut handling](../../../docs/forge/references/shortcut-resistance.md).

Render role prompts with `python3 scripts/forge.py render-prompt ROLE --context FILE.json`;
the contract lists exact inputs and nine role names. Never dispatch unbound placeholders.
Use parallel leaf agents only when available/permitted; otherwise record sequential
multi-pass execution. Do not claim independent review when self-reviewing.

After SURVEY continue autonomously within agreed scope, reopening material ambiguity or
concrete blockers. Keep status/evidence current for resumption. Never invent passing
tests, production measurements, USER decisions or permissions. Do not merge/release or
modify originals without explicit authority for that action. No internal services,
API keys, hardcoded models, hosted worker or paid integration is required by this skill.
