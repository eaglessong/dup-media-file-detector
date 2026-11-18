# Conditional capture and provenance

Adapted from forge's live-wire capture discipline. This local scanner does not need a
live service or a personal NAS library for every feature. Captures apply when a claim
rests on an external contract not established by existing faithful fixtures.

## Triggers and early probe

Start in PROSPECT when changing a decoder/metadata parser or wire-format constant,
introducing an external API/tool/storage target, claiming support for a new platform,
or relying on a cheap-to-check load-bearing premise about actual boundary behavior.
Record target/version, case, expected observation and why existing fixtures are inadequate.
A local exact-byte or extension-selection change normally uses synthetic files only.
A new platform claim needs actual platform evidence; a simulated path is not a NAS run.

## Procedure

Use the smallest authorized disposable sample. Prefer official public/licensed samples
or synthetic valid media. For a service use existing authorized credentials only, never
hardcoded tokens. Do not call paid endpoints, upload media or access private stores merely
because a capture would be useful; those actions require their own task authority.
The coordinator runs the probe, not the read-only leaf reviewer. Record command/tool,
version/platform, date, response status/encoding/shape or observed filesystem behavior.

Keep raw output outside tracked paths and out of shared command logs when sensitive.
Before staging, sanitize content and identifiers deterministically for the known format,
then inspect the whole fixture/diff for secrets, private paths, EXIF/location/account
metadata and embedded media. A generic regex is not proof binary data is safe. Unknown
sensitive formats must stay out of Git until a safe sample or suitable sanitizer exists.
No capture/redaction tool is bundled: the original enterprise credential redactor does
not establish safe media/EXIF sanitization and is deliberately not copied.

Preserve semantics that the test asserts; don't rename real fields to match the code.
Commit only the minimal safe fixture plus provenance/license and an assertion exercising
it, not raw credentials or personal media. Distinguish captured, synthetic, docs-derived
and owner-supplied data; do not turn a scrubbed log excerpt into a claimed wire capture.

## Completion and gaps

Maintain a matrix of target/case, trigger, source, sanitization, consuming test and result.
If capture is not triggered, say N/A with the scope reason. If a necessary capture cannot
be obtained safely, record the missing premise and block its support claim or narrow the
feature with an explicit design decision. A limitation is not evidence that the broader
claim passed. Never downgrade a data-loss/privacy blocker to an undocumented waiver.
A reproducible synthetic case can close a local logic claim; it cannot certify an
unavailable hardware/API behavior. Report precisely what remains unverified.
