# dup-media-file-detector

An artifact-driven project for finding duplicate media files. Application features are
not implemented yet. Describe what you want; a coding agent turns the brief into a
design, implementation, tests, and a reviewable pull request.

## Start without writing code

1. Open this repository in Codex or Claude Code. The agent reads `AGENTS.md` or `CLAUDE.md`.
2. Edit [`docs/PRODUCT.md`](docs/PRODUCT.md): describe your users, media collection,
   desired experience, and constraints in ordinary language. Unknowns can stay open.
3. Tell the agent:

   > Follow the forge workflow. Create feature `first-scan` from docs/PRODUCT.md and
   > docs/design/first-scan.md. Explore first, ask about consequential unknowns,
   > then implement, test, review, and open a PR. Do not merge it.

   You may ask the agent to write the design from your brief, or author it yourself.
   [`docs/design/first-scan.md`](docs/design/first-scan.md) is a proposed starting point,
   not a decision that you have already made.
4. Review the agent's plain-language PR summary, demo instructions, decisions, test
   evidence, and limitations. Request revisions in ordinary language. Merge when ready.

For subsequent features, ask the agent to run:

```sh
python3 scripts/forge.py new-feature my-feature
```

Then edit `work-items/my-feature/brief.md`, or explain the feature in chat and ask the
agent to fill it in. Track progress in `work-items/my-feature/status.json` and the
adjacent evidence file. You never need to maintain that bookkeeping yourself.

## What is included

- A portable [six-phase workflow](docs/WORKFLOW.md), with design and ADR templates.
- `/forge` for compatible skill-enabled agents in `.agents/skills/forge/` and
  `.claude/skills/forge/`. If slash commands are unavailable, say “follow the forge
  workflow”; the same instructions work through `AGENTS.md`.
- GitHub feature/bug forms, a PR template, and a starter framework CI check.
- A Python 3.11+ standard-library scaffolder and framework validator; no API key or
  dependency installation is needed for these tools.

This adapts the phases and evidence discipline of Cowork's forge process. It is an
independent starter: no internal services, credentials, telemetry, proprietary code,
or organization-specific automation are required. The workflow guides an agent you
run; it does not provision an autonomous hosted agent or spend an API budget.

## Verification

```sh
python3 scripts/forge.py check
python3 -m unittest discover -s tests -v
```

CI initially validates the framework only. The first implementation PR must add and
run application format/lint/build checks as applicable, integration tests, and an
end-to-end test through the real user entry point. Framework checks alone never prove
application correctness. Python is tooling here; the application language, packaging,
UI, and supported platforms are still design decisions.

## Media safety

Detection is read-only by default. Exact byte equality and perceptual similarity are
different results. Any future delete/move capability needs its own design, explicit
user intent, preview, and recovery strategy. Never use your personal media library as
a disposable test fixture.
