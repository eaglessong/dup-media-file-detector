# Evidence and report contract

## Grounding gates

Every defect finding must survive all four gates. Keep role attribution and deduplicate
shared root causes. Cite lines verified in the reviewed snapshot; source excerpts are
short receipts, not pasted files.

| Gate | Required evidence | If missing |
| --- | --- | --- |
| E — Evidence | Changed site and supporting code actually read this run, with file:line and role | Drop unread or remembered claims |
| I — Impact | Concrete trigger, consequence and named downstream consumer with file:line, or explicit no-consumer explanation | Drop unsupported blast radius |
| R — Real | A defect demonstrated from source or existing evidence, not merely an unobserved hypothetical | Move to Leading questions; retain serious unresolved safety uncertainty as a limitation |
| D — Discriminating | Explain why the evidence supports this defect rather than an equally valid working interpretation; address counter-evidence | Demote disputed interpretations or drop preferences |

A grounded policy/artifact violation can cite its actual rule and changed instruction
as the affected consumer; no fictional runtime caller is needed for review-tooling
changes. A PR-description contradiction cites the verbatim claim plus contradictory
source; unsupported prose alone is not a source defect. Suggested experiments remain
unrun until separately authorized. Do not claim a hypothesis was refuted by reasoning
when the required external evidence is missing.

## Priority and verdict

- P0: immediate, demonstrated severe data loss/security exposure or universally unusable
  critical behavior. Use sparingly; missing tests alone are never P0.
- P1: high-impact correctness/safety/privacy or broken primary behavior; fix before delivery.
- P2: concrete narrower correctness gap, material acceptance-test/rule gap, or operability
  regression. Blocking when it violates accepted requirements or conceals a material defect;
  otherwise advisory, with the reason explicit.
- P3: optional, actionable maintainability improvement. Advisory. Avoid stylistic noise.

Blocking/advisory status follows demonstrated impact and accepted requirements, not
which reviewer spoke. Do not import Aether's persona-specific P0 or approval policies.
Any blocking finding gives **CHANGES REQUIRED**. If the intended review cannot be
completed or material safety evidence remains unresolved, give **INCOMPLETE**, including
known blockers. Otherwise give **NO BLOCKING FINDINGS**, with advisories and limits.
A clean verdict does not certify tests passed, PR approval, merge readiness, or safety
of deleting media. Distinguish source-level confidence from empirical verification.

## Synthesized report

Use this shape, omitting inapplicable PR-specific details rather than fabricating them:

```markdown
# Code Review — target

- Target/repository and scope:
- Base, head, merge-base; dirty/untracked snapshot digest:
- Mode: Quick | Full
- Execution: delegated roles | single-agent multi-pass | single-agent (Quick)
- Independence: known author/reviewer overlap; self-review of reviewer rules if applicable
- Coverage/exclusions; unavailable evidence:
- Test impact: required suites and assertions; run evidence or NOT RUN
- CI: reviewed SHA, observed check SHA/state, or unavailable
- Synthesis: draft count → retained, demoted, dropped (count unique root causes)
- Verdict: CHANGES REQUIRED | INCOMPLETE | NO BLOCKING FINDINGS

## Blocking findings
- F1 [P1] [role] path:line — defect and concrete trigger.
  Evidence/consumer: source receipt and affected call site (or explicit no-consumer).
  Impact: observable consequence. Correction: actionable direction.
  Verification: assertion/experiment needed; run/not-run status.

## Advisory findings
Same evidence standard; explain non-blocking disposition.

## Leading questions and limitations
Unsettled hypotheses, missing context, and discriminating evidence needed.

## Devil's Advocate
Missed classes, novel stress hypothesis or NONE with search log, counter-evidence,
clean areas rechecked, and synthesis disposition. Quick: N/A.

## Dropped or demoted findings
Finding ID and role, failed gate/counter-evidence, and reason.

## Reviewer coverage and verdicts
Role → inspected areas, findings/verdict, and limitations; do not invent agents.

## Verification recommendations
Relevant commands from current CONTRIBUTING/CI, explicitly unrun unless evidenced.
```

Keep the report concise per finding but include all supported defects. For delegated
runs use the same finding fields in each role's response. The final synthesis, not a
concatenation of role outputs, is the deliverable.
