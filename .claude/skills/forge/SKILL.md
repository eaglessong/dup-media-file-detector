---
name: forge
description: Build features from a brief or design through reconnaissance, decisions, implementation, behavioral verification, adversarial review, and a reviewable PR. Use for feature implementation in this repository.
argument-hint: feature brief, design path, or desired behavior
---

# Forge

Read `AGENTS.md`, `docs/PRODUCT.md`, and `docs/WORKFLOW.md`. Follow that workflow as the
canonical process. Treat the user's argument as a feature request or artifact path.
Explore before clarifying, write the design before implementation, and keep status and
evidence current. Use `python3 scripts/forge.py new-feature <slug>` for missing artifacts.
Resolve material questions during SURVEY, then execute within authorized scope through
implementation, integration and entry-point E2E testing, adversarial review and PR.
Never claim unrun tests, independent review, or product-owner decisions without evidence.
Do not merge without user authority. This skill requires a running coding agent; it
neither launches a hosted agent nor configures paid credentials.
