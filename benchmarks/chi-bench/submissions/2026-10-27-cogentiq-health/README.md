# Fractal AI Research · Cogentiq Health · Vaidya-agent-os

Submitted: 2026-10-26 · chi-bench chi-bench-v1.0.0 · pass@1: **61.3%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 72.0% | 25 |
| pa_um | 52.0% | 25 |
| cm | 60.0% | 25 |

## Contacts

- [Kalash Shah](mailto:kalash.shah@fractal.ai)
- [Kunal Singh](mailto:kunal.singh@fractal.ai)

## Contributors

- Kunal Singh (Team Lead)
- Kalash Shah*
- Anannay Jain*
- Pradeep Moturi

* Equal contribution
## Inspect a trajectory

```bash
zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .
```

Trajectories are sanitized public exports with standardized system and
initial user prompts. Private tool activity and sensitive implementation
metadata have been removed. Verifier results and original execution
timestamps are preserved; original run records remain private.

See `submission.json` for the full manifest and `provenance.json` for
the published provenance. This packet combines three domain-specific
runs; no shared code revision or image digest is asserted.
