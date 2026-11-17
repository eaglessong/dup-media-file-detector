# Review roles

Used by `/code_review`. Each selected role reads the shared evidence/report contract
in `docs/code-review/report.md`. These are functional checklists adapted from Cowork's
reviewer personas, not impersonations of individual people or external review bots.
Read the actual changed files and relevant callers, not just hunks. For large files,
read each changed function, callers/callees, and lifecycle/error handling around it;
disclose unread sections. Follow consequential cross-file dependencies.

## architecture

Trace the feature's advertised effect from the shipped entry point to its consumers.
Check newly computed values reach their sinks, callers follow changed contracts, and
newly activated paths do not expose untested destructive behavior. For changed branches,
identify the behavioral assertion that would fail if the change were reverted; do not
promote every missing unit test into a critical defect.

For this scanner, inspect exact-byte proof versus size/hash candidates, empty files,
hash collisions, duplicate grouping and ordering, hardlink/storage identity, live-file
mutation detection, traversal containment, and file-descriptor lifetime. Trace values
through SQLite and JSON. For stateful changes inspect transactions, retries, cancellation,
crash cleanup and concurrency; construct a concrete failing sequence before calling it
a defect. Check sibling implementations and boundary inputs. Challenge stated safety
bounds, including whether the same user's retry or prior scan violates a claimed limit.

## operational-summary

Compare PR/design claims with the implementation and docs. Check old names and imports,
CLI options/defaults, stdout JSON vs stderr diagnostics, schema/exit codes, compatibility,
installation on supported Python/POSIX environments, temp-space requirements, permission
failures, disk-full behavior and cancellation. Do not call documented unsupported NAS
hardware a regression without evidence of a conflicting requirement.

Confirm logical byte totals are not advertised as reclaimable disk space and inventory
output does not implicitly authorize future deletion. Compare run instructions against
what exists. Record GitHub checks only for the reviewed SHA; missing, skipped, pending,
or older green checks do not prove this revision passed. Do not inherit suppression
lists or required-check names from Aether; inspect this repository's actual workflows.

## deep-read

Read full control flow around every hunk: exceptions, early returns, descriptor closing,
SQLite/tempfile lifecycle, signal handling, and publication of partial results. Inspect
symlink replacement and path races, descriptor-relative operations, overlapping roots,
special files, unreadable/undecodable names, large trees, bounded memory/open files,
private paths in exceptions, and unintended network/content writes where relevant.
Root-relative inventory paths are intentional product output; distinguish them from
leaking absolute roots in diagnostics.

Follow config/output consumers and fixtures outside the diff. Check weakened assertions,
deleted cases and skips against the intended behavior. Compare docs and test claims to
source. Report concrete missed co-changes; avoid speculative best-practice inventories.

## test-impact

Determine which existing verification suites cover the changed behavior and what is
missing. Read `CONTRIBUTING.md` and actual CI; don't invent a formatter, coverage floor,
external eval suite, or production environment. Return an impact decision with test paths,
assertions, relevant commands, and recorded evidence SHA, or explicitly “not run”.

- Framework/skills/docs: framework validation, scaffold/validator tests as applicable,
  plus manual or behavioral skill evaluation when instructions change execution.
- CLI/output changes: application contract tests and real subprocess E2E cases.
- Scanner/filesystem/SQLite changes: integration plus shipped-entry-point E2E cases
  for the changed behavior, including safety, negative inputs and failure states.
- Tests/fixtures/CI only: examine which behavior can now regress undetected; these
  changes are not automatically exempt from behavioral impact.

Ask whether a test can pass with the feature removed, compares output to itself, mocks
away the actual filesystem contract, or verifies liveness rather than correctness.
Require evidence for meaningful acceptance-test gaps; an unrun test belongs in
verification context and is not automatically a source-code defect. Do not run tests.

## repository-rules

Apply only rules actually present in the reviewed tree's `AGENTS.md`, accepted design,
ADRs, `docs/WORKFLOW.md`, and contribution guidance. For each applicable rule record
PASS, VIOLATION, or UNVERIFIED with a source and evidence; N/A is allowed with scope.
Prioritize original-file preservation, exact vs approximate proof, traversal boundaries,
no unauthorized uploads/destructive operations, fixture provenance/privacy, truthful
decision attribution, test evidence, and docs/contracts accompanying behavior changes.

Inspect changed workflow permissions/actions, validators, skills and generated status
for bypasses: structural validation is not behavioral proof. Check paired skill entry
points for drift. Do not impose Aether's telemetry stack, deployment policies, review
bots, approval rosters, or merge rules. A preference is not a project-rule violation.

## Devil's Advocate (after the draft)

Search the changed files and relevant callers for hazard classes the draft missed:
file mutation/TOCTOU; root/symlink escapes; fail-open or swallowed errors; resource or
SQLite/temp-space exhaustion; cancellation/partial output; privacy; incorrect exact
matching or hardlink accounting; defaults/schema/CLI drift; tests that assert a defect;
and agent/CI instructions that weaken verification. Scope searches to the change.

Challenge claims that the draft calls clean and any disclosed residual's claimed bound.
Try the same user's previous run, retry, or interruption as the cheapest second actor.
Report counter-evidence against draft findings, with file/line search receipts and what
would settle the dispute. Propose one novel, concrete stress hypothesis and the evidence
that would discriminate it, if one is supported; otherwise record NONE with the searches
performed and their limits. Do not manufacture a hazard or rerun application code.
