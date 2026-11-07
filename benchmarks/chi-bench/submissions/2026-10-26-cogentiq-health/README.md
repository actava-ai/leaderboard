# Fractal AI Research · Cogentiq Health · Vaidya-agent-os

Submitted: 2026-10-26 · chi-bench chi-bench-v1.0.0 · pass@1: **61.3%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 72.0% | 25 |
| pa_um | 52.0% | 25 |
| cm | 60.0% | 25 |

---

## About Vaidya

Vaidya is Fractal AI Research's healthcare AI model, post-trained on proprietary data. It scores **50.1% on HealthBench-Hard**, a new state of the art under the prescribed protocol. Learn more about our work at [Fractal AI Research](https://fractal.ai/ai-research/).

**Our recent Publications:**

- ["Fathom-Vaidya: Advancing Medical Reasoning with Rubric-Based Rewards"](https://arxiv.org/abs/2609.24480) [EMNLP Main 2026]
- ["Fathom-DeepResearch: Unlocking Long Horizon Information Retrieval and Synthesis for SLMs"](https://arxiv.org/abs/2509.24107) [ICLR Main 2026]
- ["VAIDYA: Validated Agents for Intelligent Diagnosis and Yielded Analysis"](https://link.springer.com/chapter/10.1007/978-3-032-30813-9_6) [AMIE Main 2026]

---

## Contacts & Contributors

- Kunal Singh (Team Lead) · [Contact](mailto:kunal.singh@fractal.ai)
- Kalash Shah* · [Contact](mailto:kalash.shah@fractal.ai)
- Anannay Jain*
- Pradeep Moturi

(*) Equal contribution

---

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

---
