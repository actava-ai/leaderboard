# chi-bench

Submissions to the chi-Bench benchmark — long-horizon, policy-rich U.S. healthcare workflow agents across provider prior authorization, payer utilization management, and care management.

**Producer:** [actava-ai/chi-bench](https://github.com/actava-ai/chi-bench)
**Current dataset version:** `chi-bench-v1.0.0`
**Schema:** [`schema/submission-v1.json`](schema/submission-v1.json)

## Producing a packet

On the chi-bench side:

```bash
uv run cb submission prepare -f configs/submissions/<your-id>.yaml
# Packet ready: logs/submissions/<id>/packet/YYYY-MM-DD-<id>/
```

See chi-bench's [packet contract](https://github.com/actava-ai/chi-bench/blob/main/docs/submission-packet.md) for the directory shape.

## Submitting

Two paths, both equivalent:

**Quick (helper):**

```bash
python ../../scripts/submit.py /path/to/packet/YYYY-MM-DD-<slug>/
```

**Manual:**

```bash
git clone https://github.com/<you>/leaderboard && cd leaderboard       # your fork
cp -r /path/to/packet/YYYY-MM-DD-<slug>/ benchmarks/chi-bench/submissions/
python scripts/validate.py benchmarks/chi-bench/submissions/YYYY-MM-DD-<slug>/
git checkout -b sub/chi-bench/YYYY-MM-DD-<slug>
git add benchmarks/chi-bench/submissions/YYYY-MM-DD-<slug>/
git commit -m "chi-bench: <team> · <agent> · <model>"
git push origin sub/chi-bench/YYYY-MM-DD-<slug>
gh pr create --base main
```

## Inspecting a trajectory

```bash
zstdcat benchmarks/chi-bench/submissions/<dir>/trials/<domain>/<trial_id>/agent/trajectory.jsonl.zst | jq .
```

Line 1 is the ATIF header; subsequent lines are individual agent steps.

## Headline metrics

`submission.json:results.overall.pass_at_1` is the leaderboard's primary ranking metric. Per-domain breakdowns live in `results.per_domain.{pa_provider,pa_um,cm}`. Cost (`mean_cost_usd`) and walltime (`mean_walltime_s`) are recorded but not currently ranked.
