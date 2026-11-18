# Cowork forge adaptation map

This is a process/prompt adaptation, not a copy of Cowork product code or infrastructure.
The source is Cowork's forge skill, its nine role prompts and five references. The port
keeps the phase and instrument distinctions while using this repository's accepted
product and agent rules. No internal hostname, account, dataset or cloud service is needed.

| Source material | Adaptation here |
| --- | --- |
| Phase prerequisites, LIGHT/FULL, autonomous execution and context discipline | docs/WORKFLOW.md and the paired forge skill entry points |
| Five PROSPECT prompts | docs/forge/prompts/: history, architecture, workload, test landscape, premise challenge |
| Four ASSAY prompts | Implementation challenge, local scale/resource evidence, diagnostics/security and test realism |
| Decision records | Existing feature designs and shared docs/decisions/; attributed USER/AGENT decisions and explicit reversals |
| Test-data protocol | Synthetic real-filesystem fixtures, licensed valid media when needed, supported-platform environment evidence |
| Live-capture protocol | Conditional parser/platform/external-contract probes with minimal safe fixtures and provenance |
| Shortcut resistance | Honest scope reduction and gate evidence; explicit user authority preserved |
| Knowledge map | Actual Python CLI/scan/index/tests/framework/review navigation |
| Credential redactor script | Not ported: enterprise identifier scrubbing does not establish safe personal-media/EXIF redaction |
| Production telemetry, token server, Redis/deployed pod topology, Rust/organization merge gates | Not applicable; actual local workload and project CI replace them |

The standalone code-review command remains review-only. Forge's ASSAY supplies additional
instrument-specific tasks/results to its role/challenge/synthesis process, then forge
owns fixes and reruns. This avoids two duplicate reviewer panels and preserves the
standalone review boundary. All nine prompts are read-only leaves.

Tooling validates required supporting files, skill mirrors and prompt input contracts,
and renders fully bound prompts. It does not dispatch workers or prove workflow compliance.
Sequential role fallback is explicit; multiple role labels are not independent review.
