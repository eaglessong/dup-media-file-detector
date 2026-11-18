# Full forge workflow port — execution evidence

## Scope and PROSPECT

FULL: changes agent/verification instructions and framework tooling. Read the source
forge phase guide, five PROSPECT and four ASSAY prompts, decision/test-data/shortcut
references and capture/knowledge-map structure. Compared to the existing short forge
router, canonical workflow, code_review integration, scaffolder/validator, templates and
tests. Source adaptation and omissions are mapped in docs/forge/PORTING.md. No company
code, credentials, personal media or internal endpoint is introduced.

Test-data verdict ADEQUATE: deterministic prompt-context dictionaries, disposable copied
artifact trees and isolated Git repos faithfully test tooling contracts; no decoded
media or live service is needed. Application behavior is unchanged.

## SURVEY/SMELT

The owner explicitly requests key phases, applicable prompts and support materials.
No material product choice is needed for this process-only port. AGENT choices and R1–R6
are recorded in docs/design/forge-workflow-port.md before application of implementation.
All shared material is repo-root docs/forge; paired skill entry points remain identical.

## Implementation

Implemented nine distinct leaf prompts, six protocols, canonical phase gates/risk tracks,
code_review integration, template updates, source adaptation map and standard-library
prompt rendering/resource validation. No dispatcher or hosted worker is provisioned.
No application code was changed.

## Verification

- Framework check: exit 0 in staging and target repository.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`: 15 tests, exit 0
  from the project root. Includes all-role bindings, malformed/missing/unknown inputs,
  missing resources, unsafe/broken links, skill drift and real renderer CLI success/error.
- An initial absolute-path discovery invocation from the unrelated working directory
  failed to import dup_media. Corrected the invocation cwd and reran successfully;
  no application fix was needed and the failed attempt is not counted as a pass.
- Skill-creator quick_validate: both forge entry points pass using PyYAML already
  installed only in temporary validation tooling. No project dependency was added.
- `git diff --check`: exit 0. Check again after final review/artifact updates.

## ASSAY — actual review and evaluation

Separate independent subagents evaluated the substantially revised skill and reviewed
the actual dirty port using code_review, with delegation disabled and no app/test/network
execution in either review. Read-only review covered the actual tooling, tests, paired
skills, canonical workflow, all nine prompts/six references and scoped artifacts.

F1 (P2 blocking, test realism): the original escape regression test targeted a nonexistent
outside file, so existence rejection could conceal loss of containment. FIXED: use an
existing external file and a symlink, test both validator and renderer, and rerun. In an
isolated mutant removing containment while retaining existence checks, the strengthened
test failed (exit 1). The independent re-review verified the source fix and returned no
blocking findings; the mutation command itself was coordinator-run, not independently run.

F2 (P2 advisory): generated Markdown links could break with checkout names containing
spaces. FIXED after that re-review: angle-bracket destinations, plus an actual copied
checkout named `checkout (with spaces)` verifying linked support-file existence and
rendered syntax. Final small change was coordinator-reviewed and tests rerun. Do not
claim the independent reviewer executed these tests or approved a later unseen snapshot.

Independent design-only forward-test used an isolated project copy with a realistic
CSV-export request and no implementation/test/publication authority. It followed FULL,
rendered five PROSPECT prompts, used labelled sequential passes, recorded safe AGENT
choices/feasible test plans, and wrote a design/ADR/evidence without changing application
code. It exposed missing design-handoff state, scratch prompt links and unclear
fixture-planning requirements. FIXED: design-delivered state and regression test,
absolute support links rebased before context substitution, and explicit design-only
guidance. The follow-up rendered all five prompts into scratch, opened their canonical
support links, recorded design-delivered and passed framework validation. It reported no
remaining blocker; five-prompt repetition is acknowledged overhead.

Test-realism accounting: the independent initial review read five new tests (four HONEST,
one DEAD for F1). Its re-review found the six then-added tests source-level HONEST. The
final seventh added test covers F2 and was reviewed by the coordinator. All 15 top-level
framework/application-contract tests actually passed. No unresolved LYING/DEAD finding.
No external capture is applicable to this process/tooling change. Measurements concern
only prompt/tooling behavior; no NAS performance claim or personal data was used.

## STAMP and limits

Source design and templates were updated with actual findings. Application code is
unchanged. Live client slash-command discovery, delegated parallel implementation,
external API captures and full end-to-end feature execution were not exercised. This is
instruction-driven workflow validation, not proof of an autonomous orchestration service.
Local application integration/E2E suites were not rerun for this framework-only change;
GitHub application CI is expected to execute them on the PR, and actual results must be
recorded rather than assumed.

Branch: codex/port-forge-workflow. PR creation and CI observation are the remaining
STAMP steps. No merge is authorized by this request.
