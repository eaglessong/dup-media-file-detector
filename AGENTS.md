# Agent instructions

Read `docs/PRODUCT.md` and `docs/WORKFLOW.md` before feature work. The user's intent and
accepted design artifacts define the product. Ask focused questions only for missing
information that materially changes behavior, safety, architecture, or acceptance.
Record assumptions as AGENT decisions; never attribute them to the user.

## Execution contract

- Follow PROSPECT → SURVEY → SMELT → FORGE → TEMPER → ASSAY → STAMP as documented.
  SURVEY is the clarification checkpoint between exploration and design.
- Use `python3 scripts/forge.py new-feature <slug>` to create missing artifacts.
  Update the brief, design, status, and evidence as work progresses and before handoff.
- Author the design before implementation. Continue autonomously within the agreed
  scope; artifact authorship is the user's primary interaction, not direct coding.
- Keep changes small and reviewable. Use `codex/<slug>` branches in Codex. Do not
  overwrite unrelated work. Use Conventional Commits and never invent author identity.
- Read-only scanning is the default. Do not follow symlinks outside selected roots,
  upload media, delete, rename, or modify originals without a specific accepted design.
- Separate exact duplicate proof from similarity ranking. Never recommend deletion
  based only on approximate fingerprints or metadata. Design for files changing during
  scanning, permission failures, cancellation, and large directories.
- Use small synthetic or licensed fixtures with provenance; no personal media,
  credentials, raw private paths, or copyrighted sample collections in Git.
- Derive tests from requirements and failure modes. Exercise real filesystem behavior
  in temporary directories and the actual shipped entry point for E2E validation.
- Add actual application checks to CI in the first implementation PR. Do not claim
  framework validation is an application test, or fabricate successful command results.
- Perform adversarial review after tests, resolve findings, and rerun affected checks.
  `/code-review` provides the review-only role/challenge/synthesis process; during forge
  use it for ASSAY, then return to forge to fix findings and rerun affected checks.
  If supported and authorized, use an independent reviewer; otherwise do an explicit
  second review pass and label it self-review. Never claim independence falsely.
- Open a PR when GitHub is available and the task authorizes delivery. Include a short
  user-facing demo, decisions, test evidence, review findings, and remaining risks.
  Read CI plus PR conversation, reviews, and inline comments; fix failures and findings.
- `/ship-it` owns the authorized PR feedback/CI/merge lifecycle; its shared playbook is
  docs/ship-it/iteration-playbook.md. Explicit --no-merge survives resume. Installing the
  skill or invoking forge/code-review alone does not authorize merge.
- Do not merge, publish a release, or enable destructive behavior without user authority.
  Missing credentials or necessary product decisions are concrete blockers to report.

## Framework maintenance

Run `python3 scripts/forge.py check` and
`python3 -m unittest discover -s tests -v` after changing the framework. Keep matching
forge, code-review and ship-it skill entry points identical across agent integrations. Use only Python's standard library
for framework tooling unless a design justifies a new dependency. Forge's shared prompts
and protocols live in docs/forge/; bind prompts with scripts/forge.py render-prompt and
validate references/contracts with scripts/forge.py check. The application uses
Python 3.11+ with SQLite and POSIX filesystem APIs; see CONTRIBUTING.md.
