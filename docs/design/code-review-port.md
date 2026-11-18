# Local code-review skill

**Status:** Implemented — prepared for owner review

## Problem and current state

Forge has a generic ASSAY review phase but no reusable dedicated review command.
The existing application is a Python/SQLite/POSIX read-only media scanner, with CLI,
integration and E2E checks documented in CONTRIBUTING.md.

## Requirements and non-goals

- R1: Expose the requested `/code-review` name in both agent skill directories.
- R2: Review working changes, branches, patches, or GitHub PRs against the correct tree.
- R3: Preserve specialist analysis, adversarial challenge and evidence-gated synthesis.
- R4: Check local media/CLI/framework contracts without importing internal infrastructure.
- R5: Produce a local report without editing code, executing tests, posting or merging.
- R6: Disclose snapshot limitations, unrun checks, authorship overlap and fallback execution.

Non-goals: hosted bots, test execution, auto-fixes, automatic comments, or application changes.

## Alternatives and recommendation

Copying the source unchanged leaves unavailable agents, services and policies. A generic
single review prompt loses the source's challenge and evidence discipline. Adapt the
process into mirrored portable skills plus shared role/report references; use generic
subagents when permitted or clearly labelled sequential role passes otherwise.

## Architecture and interfaces

Both SKILL.md entry points are identical. Repository-root docs/code-review/roles.md
holds five role checklists plus the Devil's Advocate. report.md holds severity, evidence
gates and report shape. The skill resolves target/base/snapshot, routes roles, challenges
the draft and synthesizes one local report. Forge ASSAY invokes this review process;
fixes and reruns stay in forge. scripts/forge.py requires the new files and checks mirrors.

## Safety, privacy and limitations

Review-only operations permit reading local/GitHub data and creating disposable review
scratch/worktrees and local reports. No target code, tests or hooks should execute.
Reports stay in ignored .agent-local/reviews/. Do not mutate the user's checkout to
review another revision. Explicitly identify unknown patch bases and incomplete reviews.
Client command discovery and independent-agent availability vary; document fallback.

## Decision records

- USER: “port and adept /aether_review from Cowork to this GitHub repo. name it /code_review”.
- AGENT: functional reviewer roles replace named internal personas and bot accounts.
- AGENT: share references rather than duplicate all role text across agent integrations.
- USER (2026-11-18): “rename the skill 'code_review' to 'code-review'”. This supersedes
  the original underscore command name quoted above and the original AGENT decision
  to preserve that spelling. Both skill folders, frontmatter and invocation docs now
  use `code-review`; review behavior and authority boundaries are unchanged.
- AGENT: use the existing contribution test commands and no new project dependencies.

## Verification and delivery

R1/R4/R5: inspect mirrored files, shared paths, project rules and boundaries.
R2/R3/R6: independent forward-test in an isolated synthetic repository; inspect the
result for snapshot, role selection, concrete findings and honest verification limits.
Framework validator/unit tests cover required artifacts and mirror drift. These checks
do not prove every client discovers slash commands or guarantee reviewer reasoning.
Deliver a PR, verify GitHub CI, and leave merging to the owner.
