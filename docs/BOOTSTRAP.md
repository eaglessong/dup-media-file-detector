# Starter framework delivery

The owner requested a private `eaglessong/dup-media-file-detector` repository with an
artifact-driven development process resembling Cowork forge.

## Adaptation decisions (AGENT)

- Preserve the exploration, clarification, design, implementation, two-tier behavioral
  verification, adversarial review, and evidence-rich delivery sequence.
- Replace production-service assumptions with filesystem safety, realistic media
  fixtures, actual user-entry-point tests, and measurable local workloads.
- Use Python standard-library tooling only for the framework. Do not select an
  application stack or implement media detection before the product design is settled.
- Supply compatible skill entry points and ordinary-language invocation. Keep the
  workflow usable even when a client does not expose slash commands or subagents.
- Do not copy internal code, credentials, tenant data, private service URLs, or
  organization-specific deployment/merge policies into this standalone project.
- Leave licensing undecided rather than assign rights on the owner's behalf.

## Bootstrap verification

Run in the initial local checkout:

- `python3 scripts/forge.py check`: exit 0.
- `python3 -m unittest discover -s tests -v`: six tests, exit 0.

A separate self-review pass checked the links/paths, paired skills, template creation,
status transitions, safety instructions, and CI commands. No independent reviewer was
used. Structural validation does not attest to application correctness; no application
exists yet. GitHub CI provides a separate execution of the framework checks.
