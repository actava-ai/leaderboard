# chi-bench schema

JSON Schema files for chi-bench submission manifests.

## Files

- `submission-v1.json` — schema for `submission.json` envelope + chi-bench-specific `results.*` shape. Frozen at chi-bench v1.0.0 release.
- `known-versions.txt` — accepted `dataset.version` values, one per line. The validator's "unknown dataset version" check is a soft warning, not a failure; new versions can be added in a follow-up PR after the first submission lands.

## Versioning policy

- **`submission-v1.json` is frozen and never edited.** Submissions written against v1 stay valid forever.
- A new version (`submission-v2.json`) lands alongside it if backward-incompatible changes are required (e.g. the chi-bench v2 dataset removes a domain). Producers update their tooling to emit the new `schema:` string when they target the new dataset version.
- Adding a new optional field to v1 is acceptable iff the schema's `additionalProperties: true` already permits it (it does — at the envelope level and inside `results.*` and `provenance.*`).
