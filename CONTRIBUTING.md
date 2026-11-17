# Contributing through artifacts

Open a feature issue or edit `docs/PRODUCT.md` / a feature brief. Explain the behavior,
examples, constraints, and what success looks like; implementation details are optional.
Ask your coding agent to follow `docs/WORKFLOW.md` and deliver a PR.

Framework tooling requires Python 3.11+ and Git. Run:

```sh
python3 scripts/forge.py new-feature example-feature
python3 scripts/forge.py check
python3 -m unittest discover -s tests -v
```

The first command creates editable artifacts, not application code. Do not commit
throwaway example features. The application stack is undecided. The first application
PR must document installation, build, format/lint, integration and E2E commands here,
and run applicable checks in CI. Do not replace real application tests with the
framework validator.

Use a feature branch, small Conventional Commits, and the PR template. Keep personal
media and private absolute paths out of fixtures and reports. All tests must operate
on temporary files or checked-in fixtures, never a user's media collection. Large
binary fixtures require a deliberate storage decision. A project license has not yet
been chosen; do not assume public redistribution rights for contributions or fixtures.
