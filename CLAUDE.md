# Project instructions

Read and follow `AGENTS.md`. The canonical feature-development procedure is
`docs/WORKFLOW.md`. Use `/forge <feature or artifact path>` when the local skill is
available; otherwise follow the same procedure directly. Do not merge PRs without
user authority.

Use `/code_review` for a local review of a working diff, branch, patch, or GitHub PR.
Its skill is review-only; it does not edit code, run tests, post reviews, or merge.

Use `/ship-it [PR] [--no-merge]` for the PR feedback/CI/fix lifecycle. Explicit shipping
intent authorizes an ordinary gated merge of that PR; porting the skill does not.
Shared playbook and resumable-state guidance live in docs/ship-it/.
