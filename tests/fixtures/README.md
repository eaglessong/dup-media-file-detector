# Test fixture provenance

Prefer deterministic synthetic files in temporary directories for exact-byte tests.
When valid media is necessary, record each checked-in fixture's generation command or
source URL, license, purpose, and expected result. Never commit personal media or
sensitive filesystem paths. Integration and E2E tests should agree on expected groups.
