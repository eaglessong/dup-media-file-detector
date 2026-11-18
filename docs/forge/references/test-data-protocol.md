# Test data and environment gate

Assess before design, then revisit when scope changes. For each requirement list the
observable behavior, representative success/failure/boundary case, required fixture,
source/provenance, environment, test tier and remaining gap.

Preferred sources for this repository:

1. Existing project fixtures/assertions, inspected for relevance and provenance.
2. Deterministic generated temporary files/trees for exact-byte/filesystem properties.
3. Small valid synthetic or licensed media when decoding/metadata/similarity requires it.
4. Supported-platform captures or official external-format samples when that boundary
   is actually involved; follow the capture protocol and label docs-derived data honestly.
5. Specific owner-provided sanitized samples only when safe synthetic/official sources
   cannot reproduce the behavior. Do not request a private collection by default.

Sources need not be exhausted in order: use the cheapest source that faithfully exercises
the claim. Bytes labelled .jpg test extension selection/equality, not image decoding.
Same size, SHA candidates and actual byte equality are different contracts. Never mock
away the filesystem race, permissions, descriptor or subprocess boundary under test.

Cover affected cases such as duplicate/different/empty bytes, nested trees, Unicode and
invalid filename encoding, symlinks/hardlinks, source replacement/mutation, permissions,
large/sparse files, SQLite disk-full/cleanup, and cancellation. Share expected groups,
errors and exit outcomes between integration and CLI E2E fixtures where useful.

Verdicts:
- ADEQUATE: required cases have realistic data and an executable environment/CI plan.
  A planned run is not yet a pass; completion still requires actual evidence.
- PARTIAL: named gaps can be remedied with disposable fixtures or available tooling;
  remediate and reassess before relying on them.
- BLOCKED: a necessary property cannot be exercised with available data/environment;
  identify exactly what is missing and the narrow path to unblock. Stop the affected
  implementation/completion claim; continue unrelated authorized work if useful.

Record fixture recipes/source URLs/license, purpose, expected behavior, capture date
when relevant, and any redaction in tests/fixtures/README.md. Never commit personal
media, absolute private paths, credentials or large unreviewed binaries. Keep raw captures
ignored, and review all generated output before staging. Test preconditions matter:
root bypasses Unix permission modes; a filesystem/OS can lack a race or signal behavior.
Missing preconditions produce an explicit gap/skip, never a fabricated pass. Supported
CI evidence can close a local gap only after the actual run succeeds at the relevant head.

For design-only delivery, assess the feasibility of fixture recipes and the planned
environment rather than claiming tests executed. Record unknown platform availability
as an implementation precondition, not a fictional design blocker if the design can
state the dependency honestly. Use phase design-delivered; implementation resumes its
normal fixture and execution gates. Never label an unrun design plan a passing test.
