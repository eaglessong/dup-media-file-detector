# First scan — execution evidence

## PROSPECT and test data

2026-11-17: Read AGENTS.md, workflow, product, first-scan brief/design, forge skill,
README, contribution guidance, CI, status/evidence, validator and fixture guidance.
`rg --files --hidden -g '!.git/**'`: framework only; no application or application CI.
`git status --short --branch` / `git diff`: owner edits in product, design and brief;
preserved their intent while revising artifacts. Created `codex/first-scan`.
Product supplies Python, Synology/Linux-like CLI, recursive exact inventory, potentially
hundreds of GB, no scan-time limit, preservation of originals. No NAS available locally.
Fixtures: generated temporary synthetic bytes, Unicode names, empty files, links,
FIFO, mode restrictions, sparse files; provenance in tests/fixtures/README.md.

## SURVEY and decisions

Asked after repository exploration. USER selected media extensions, JSON relative-path
inventory, skipping symlinks and retaining hard-linked paths with shared storage IDs.
Actual answers and separate AGENT defaults: docs/decisions/001-first-scan.md.
Design authored before application implementation. AGENT defaults include Python 3.11+,
stdlib POSIX APIs, one root, extension overrides, SQLite scratch index, SHA-256 candidate
filter plus byte comparison proof, explicit exit codes and live-filesystem limitations.
No independent agent was requested; ASSAY is self-review.

## Implementation and requirement coverage

- R1: dup_media.scan.Scan.enumerate, DEFAULT_EXTENSIONS, CLI --extensions.
  Integration: nested/Unicode/empty/filter/override; E2E expected exact group.
- R2: digest/equal/run/write; forced-hash-collision integration asserts unequal bytes
  remain separate. E2E JSON fields/group sizes and repeated deterministic output.
- R3: descriptor-relative O_NOFOLLOW opens, no source writes. Integration/E2E compare
  original bytes/names; real symlinks/FIFO excluded, root ancestors rejected.
- R4: indexed metadata checked before/after reads and final validation. Tests exercise
  mutation during hash/read, directory additions, invalid roots, actual permission
  failures and error privacy; E2E SIGINT exits 130 without a completed inventory.
- R5: SQLite index, bounded read chunks and descriptor use, streaming JSON. Hardlink
  integration checks shared storage identity. Indexed pending directories/memberships
  avoid repeated full-table scans; directory identity guard prevents traversal cycles.

## Verification runs

Local environment: macOS, Python 3.13.16, non-root. Commands below each exited 0 on
final local run after review fixes:

| Scope | Command | Result |
| --- | --- | --- |
| framework | `python3 scripts/forge.py check` | valid structural artifacts |
| framework | `python3 -m unittest discover -s tests -v` | 7 passed (6 framework, 1 application contract) |
| application | `python3 -m compileall -q dup_media` | syntax compiled |
| application | `python3 -m dup_media --help` | shipped CLI help works |
| application | `python3 -m unittest discover -s tests -p test_application.py -v` | 1 passed |
| integration | `python3 -m unittest discover -s tests/integration -v` | 14 passed, 1 Linux-only filename test skipped |
| e2e | `python3 -m unittest discover -s tests/e2e -v` | 4 passed, including actual mode restriction and SIGINT |
| application | `git diff --check` | passed |

Executed README disposable Python demo via `python3 -` (exit 0): one group containing
nested/two.jpg and one.jpg, size 21 each, total 42, complete true, no errors.
No formatter/linter/type-check dependency or package build is configured; syntax and
CLI contracts are the applicable application checks. Linux CI covers Python 3.11/3.13.
No hardware/large-library throughput benchmark or Synology compatibility claim.

Earlier runs (superseded, retained honestly): initial integration/E2E failed because
macOS temp paths contain a /var symlink, rejected by the intended root policy. Fixed
fixtures to pass canonical paths; reruns passed. A combined final-check command exited
2 due to trailing whitespace inherited from owner product prose; removed whitespace
and reran diff check successfully. No framework check was called an application test.

## ASSAY findings and dispositions

Explicit second-pass self-review of scanner, CLI, tests, documentation and CI, after
behavioral tests; no claim of independence. Findings:

- FIXED: comparison read errors could be attributed to the other operand. SourceFailure
  retains path attribution across context managers; regression asserts left read error.
- FIXED: directory changes after enumeration could evade completion checks. Persist
  directory timestamps/identity and revalidate; late-addition regression is incomplete.
- FIXED: lexical `..` normalization could hide root symlink components. Reject parent
  traversal roots; root ancestor symlink and parent traversal regressions pass.
- FIXED: SQLite cannot accept surrogate filenames as TEXT. Report unsupported encoding
  with escaped name and incomplete status. Linux-only real-byte fixture in CI.
- FIXED: pending directory and group output lookups needed indexes for many paths;
  added indexes and disk-backed SQLite temporary sorting. No benchmark claim.
- FIXED: repeated directory identities (e.g. bind aliases) must not recurse indefinitely;
  report directory_alias and skip repeated identity. Bind mounts unavailable locally.
- REFUTED: hash equality alone proves a group — forced collision test demonstrates byte
  comparison partitioning. Similarity has no implementation or deletion recommendation.
- DEFERRED, documented limitation: a live tree can change after final validation or be
  moved while open. A filesystem snapshot is required for a point-in-time guarantee.
  Inventory is observational; future actions require fresh validation.

All affected suites rerun after fixes; no unresolved blocking finding.
Final pass examined root escape, source-write paths, bounded state, exception cleanup,
SQL binding, diagnostic privacy, test assertions, and real module subprocess execution.

## Delivery

Branch: codex/first-scan. GitHub PR/CI follow-up pending at STAMP.
Initial sandboxed `gh auth status` reported invalid tokens; authenticated network-enabled
check succeeded. Default Git credential fetch failed (repository not found); per-command
GitHub CLI credential helper fetched main successfully. `git rev-list --left-right
--count origin/main...HEAD` was 0/0 before implementation commit.
Demo and invocation are in README. Main limitations: Python 3.11+/POSIX/SQLite required,
no NAS hardware validation or throughput claim, no progress/resume, live-tree consistency,
non-UTF-8 names yield incomplete inventory, shell output must be outside source root.
