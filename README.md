# dup-media-file-detector

A read-only Python CLI that inventories exact binary duplicates among media files
under one local folder, including nested folders. Original names and bytes are preserved.
No uploads, moves, deletion, or approximate similarity matching.

Requires Python 3.11+ with SQLite on Linux/POSIX. No external dependencies or install
step: copy/clone this repository onto the NAS and run from its directory. Synology
hardware has not been tested; check `python3 --version` first. All ancestors of the
selected root must be real directories, without symbolic links. Root paths containing
`..` are rejected; supply a direct path.

```sh
python3 -m dup_media /volume1/media > /volume1/inventories/media.json
# Override the default media-extension selection (no leading dots):
python3 -m dup_media /volume1/media --extensions jpg,jpeg,png,mp4,mov,mp3,flac > /volume1/inventories/media.json
```

Create the output directory first and keep output **outside the scanned root**. Shell
redirection creates/truncates the output before the scanner runs. The scanner itself
only reads originals; OS access timestamps can change as a consequence of reads.

Default extensions (case-insensitive, based on names; no media decoding):
`jpg jpeg png gif bmp tif tiff webp heic heif avif raw cr2 cr3 nef arw dng mp4 m4v mov
avi mkv mpg mpeg webm wmv mts m2ts 3gp mp3 m4a aac flac wav ogg opus wma aiff aif`.
Empty matching files are included. Symbolic links and special files are skipped.
Non-UTF-8 filenames produce an incomplete inventory with an escaped diagnostic name.

JSON contains `schema_version`, `complete`, `summary`, `groups`, and `errors`.
Every report includes a whole-scan summary, for example:

```json
{"summary": {"media_file_count": 3, "total_size_bytes": 250, "complete": true}}
```

This counts all validated selected media paths, including unique files and each hardlink.
Sizes are exact logical bytes; sparse-file holes count too. Empty matching files count
as files with zero bytes. An empty/no-matching-media tree reports zero files/bytes.
When any scan error occurs, `summary.complete` and report `complete` are false, exit
code is 1, and the count/bytes describe only validated files. Inspect `errors`; files
hidden by inaccessible directories are unknown. Partial totals are observations of a
live tree, not guaranteed lower bounds. The schema version stays 1 with an additive
summary field; strict consumers must allow that field.

Each group contains
`size_bytes`, `total_bytes` (logical bytes across all paths), and `files` with root-relative
`path` and `storage_id`. Equal storage IDs identify hard-linked paths and are meaningful
only on the scanned filesystem; total bytes do not represent reclaimable disk space.
Paths are JSON-escaped; normal output/errors omit the root's absolute path. Relative
names can still be private: treat your inventory accordingly.

Exit codes: 0 complete, 1 incomplete (inspect errors), 2 invalid invocation/root or fatal
I/O failure, 130 interrupted. Discard output after cancellation/fatal errors. Detected
changes and unreadable files prevent a complete result. Scan a quiet tree or filesystem
snapshot: a live scan cannot guarantee a point-in-time view. Future operations must
revalidate files; this inventory never authorizes deletion.

The scanner uses a disk-backed temporary SQLite index, sequential 1 MiB reads, size
filtering, SHA-256 candidate hashing, and full byte comparison. Allow scratch disk space
proportional to file count and path length. System temporary storage must be outside
the selected root. There is no progress display or resume support in this version.

## Small disposable demo

Run this from the repository. It creates only temporary synthetic fixtures, scans
them through the real CLI, prints one duplicate group, and cleans up afterward.

```sh
python3 - <<'PY'
from pathlib import Path
import subprocess, sys, tempfile
with tempfile.TemporaryDirectory() as folder:
    root = Path(folder).resolve()
    (root / 'nested').mkdir()
    (root / 'one.jpg').write_bytes(b'synthetic media bytes')
    (root / 'nested' / 'two.jpg').write_bytes(b'synthetic media bytes')
    (root / 'different.jpg').write_bytes(b'other bytes')
    subprocess.run([sys.executable, '-m', 'dup_media', str(root)], check=True)
PY
```

The demo also reports `media_file_count: 3` and `total_size_bytes: 53` with a complete
summary. The `.jpg` fixtures test binary equality and extension selection, not image decoding.

## Artifact-driven development

Describe intended behavior in [PRODUCT](docs/PRODUCT.md) or a feature brief. An agent
follows [the forge workflow](docs/WORKFLOW.md), resolves consequential questions,
authors the design, implements, tests, reviews, and delivers a PR. Do not merge without
owner authority. See [first-scan design](docs/design/first-scan.md),
[decisions](docs/decisions/001-first-scan.md), [evidence](work-items/first-scan/evidence.md),
and [contribution checks](CONTRIBUTING.md).

For a new feature: `python3 scripts/forge.py new-feature my-feature`.

## Local code review

The `/code-review` skill adapts Cowork's specialist reviewers, Devil's Advocate pass,
and evidence-grounded synthesis to this project. In a skill-enabled coding agent:

```text
/code-review
/code-review 12
/code-review full review
```

With no argument it reviews staged/unstaged changes and relevant untracked files.
It also accepts a branch, GitHub PR URL, or patch file. Reports go to the gitignored
`.agent-local/reviews/` folder. This is a review-only command: it does not fix code,
execute tests, publish comments, push, or merge. Full reviews use parallel reviewers
when supported/permitted, or explicitly labelled sequential role passes otherwise.
If the command is not discovered, ask the agent to follow
`.agents/skills/code-review/SKILL.md`. Client skill discovery may require reopening
the repository/session. The skill is named `code-review` in both agent integrations.

See the [review roles](docs/code-review/roles.md) and
[evidence/report contract](docs/code-review/report.md). During forge, this supplies
ASSAY; the implementing agent then handles fixes and verification separately.

## Full forge workflow

The forge skill includes the full [phase workflow](docs/WORKFLOW.md), five reconnaissance
prompts, four ASSAY audit prompts, and supporting protocols in [docs/forge](docs/forge/PORTING.md).
Use a feature brief or design as input:

```text
/forge implement the feature described in docs/design/my-feature.md
```

The agent explores, clarifies consequential choices, designs, implements, verifies,
reviews using code-review, and delivers a PR. It maintains your artifacts and stops
before merging unless you authorize that merge. Parallel roles are used when supported;
sequential passes are labelled honestly. Synthetic filesystem data replaces mandatory
production telemetry, and captures apply only to actual parser/platform/external-format
boundaries. No cloud/token service or personal media library is required by the framework.

For agent authors, `python3 scripts/forge.py render-prompt ROLE --context FILE.json`
binds a prompt using the [input/evidence contract](docs/forge/references/prompt-contract.md).
It does not launch agents. Framework validation catches missing resources, broken local
material links, template-input drift and mismatched skill entry points; it cannot prove
workflow execution or product correctness. See the [adaptation map](docs/forge/PORTING.md)
for what was ported and what was deliberately replaced.

## PR delivery through merge

After forge creates the PR, use the ship-it skill to handle CI/review fixes and land it:

```text
/ship-it 12
/ship-it 12 --no-merge
```

With no number it uses the current branch's PR, or follows forge STAMP to create one
if needed. Explicit shipping intent authorizes merging that identified PR after fresh
checks and feedback gates. `--no-merge` performs preparation, fixes, verification and
necessary PR replies but withholds merge; blockers remain blockers. Neither command
publishes a release or changes branch rules. Forge/code-review alone do not authorize merge.

Shared instructions are in [docs/ship-it](docs/ship-it/iteration-playbook.md), with paired
Codex/Claude skill entry points. Runs keep ignored state under `.agent-local/ship-it/`,
preserve no-merge across resume, stop at bounded rounds/repeated failures and use no
cron or background hosted worker. The local helper records progress only; actual fresh
GitHub evidence, scoped verification and user authority govern merge. If slash commands
are not discovered, ask the agent to follow `.agents/skills/ship-it/SKILL.md`.

### Publish PR reviews with patrol

`/patrol 12 --dry-run` reviews PR #12 and saves a local report without posting.
`/patrol 12` publishes actionable findings/CI context; `/patrol` sweeps eligible open
non-draft PRs updated within 24h. `--since all` widens the sweep. Complete clean reviews
with green CI need no post. The workflow never changes code, approves or merges.
See [sweep protocol](docs/patrol/sweep.md). Shared materials stay under docs/.

## Relocate duplicate media

Relocation is an explicit mode. Ordinary `python3 -m dup_media ROOT` remains read-only.
The strict Linux relocation adapter supports **64-bit Linux ext4** with effective root
and CHOWN, DAC_OVERRIDE, FOWNER and SYS_ADMIN capabilities. It refuses unsupported
filesystems/platforms and metadata; this does not certify Synology/btrfs support.
Run first on disposable fixtures, then preview your intended selection:

```sh
sudo python3 -m dup_media --move-duplicates SOURCE --destination DEST --dry-run
```

The first relative path in case-sensitive UTF-8/BINARY order stays in each exact group.
Other paths map to `DEST/<same-relative-path>`. Hardlinks count as separate paths;
unique/unselected files remain. DEST must be separate from SOURCE: equal/nested roots
in either direction and symlink ancestors are rejected before scanning. Any incomplete
scan or preflight conflict prevents all moves. Existing destination entries are never
overwritten, even when byte-identical. Both modes scan afresh; dry-run is not a reserved
plan and creates no destination or persistent journal. OS reads may update atime.

For execution, stop **all** other writers/sync/ingest jobs for both trees and ancestors,
and acknowledge exclusive access. Advisory locks only coordinate this tool; arbitrary
concurrent writers or mount changes can defeat live-filesystem checks. If exclusive
access is unavailable, use dry-run only. Choose a **new journal directory** with an
existing parent outside both trees:

```sh
sudo python3 -m dup_media --move-duplicates SOURCE --destination DEST \
  --journal /separate/location/new-operation --exclusive-access
```

Each duplicate is copied, compared byte-for-byte, checked for its platform policy, and
published without replacement before its matching source path is removed. On Linux, mode, owner,
group, exact mtime and `user.*` attributes are preserved and verified. ACLs, other xattr
namespaces and unsupported inode flags cause rejection. New inode/creation time,
ctime/link topology and read-atime effects are exceptions. Free destination capacity
must accommodate logical bytes, including independent copies of hardlinked/sparse files.

Relocation prints JSONL header/item/error/summary records. Paths are root-relative;
`planned` items describe intent and `moved` items confirm removal. Exit 0 means complete,
1 means blocked/partial, 2 means invalid/unsupported invocation/runtime, and 130 means
cancelled. Keep redirected output outside both trees. A broken pipe stops further work.
No terminal complete summary means the output does not certify success.

Batches are not atomic and completed moves are not rolled back. Failure may leave extra
source/destination/staging copies. Retain the owner-only external `journal.sqlite` and
inspect `items` states (`planned`, `copying`, `staged_verified`, `destination_verified`,
`source_removed`) alongside actual bytes/identities before manual recovery. A crash
between a filesystem action and journal commit is ambiguous. Never delete based only
on an old journal; do not blindly rerun with the same journal or overwrite prior targets.
There is no automatic resume/undo, source-directory pruning or deletion-only command.


### macOS relocation (APFS)

On 64-bit macOS, use normal user permissions (no sudo). Source, destination and journal
must be on local APFS. The same move flags apply:

```sh
python3 -m dup_media --move-duplicates /absolute/source --destination /absolute/archive --dry-run
python3 -m dup_media --move-duplicates /absolute/source --destination /absolute/archive --journal /absolute/operations/new-run --exclusive-access
```

The `macos-data-only` policy preserves exact main-stream bytes and rejects resource
forks on any duplicate-group participant. Permissions, ownership, timestamps, ACLs,
Finder tags and other xattrs are **not preserved**. New files are created mode0600;
inherited ACLs may apply. Flagged files are rejected. Scan-only mode stays read-only.
Use canonical paths without symlink ancestors; `/private/tmp` rather than `/tmp`.
JSONL header identifies the metadata policy. Linux retains strict metadata requirements.
Keep exclusive control of source/destination/journal and their ancestors throughout execution.
No automatic recovery: inspect the external journal after interrupted/partial operations.


Relocation preflight checks current effective deletion/creation permissions for the full
plan before any destination/journal mutation. macOS uses native ACL/sticky-aware checks;
readability alone does not establish move permission. Inheritable ACLs on creation
parents are conservatively rejected (`permission_inheritance_unsupported`); existing
non-inheritable ACLs are allowed when required operations are authorized. Preview does
not reserve future permissions; an execution-only journal parent is checked at execution.
