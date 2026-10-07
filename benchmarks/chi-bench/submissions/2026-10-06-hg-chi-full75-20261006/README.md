# CHI-Bench submission: hg-chi-full75-20261006

- Overall: **20/75 = 26.67%**
- Provider PA: **11/25 = 44.00%**
- Payer UM: **7/25 = 28.00%**
- Care Management: **2/25 = 8.00%**

This packet began as the completed Full75 and was then repaired only for the four evidence points explicitly requested by the CHI-Bench maintainer.

- Care `cm_mdd_hard_refuses_002`: v1.1.0 judge-only re-evaluation from the preserved final state returned **0/5** judge rubrics, so the historical pass is corrected to a fail.
- Payer P2P `t016`, `t019`, `t036`: exact v1.1.0 reruns with the historical Full75 HG agent snapshot and `CHI_BENCH_P2P_SIMULATOR_MODEL=claude-sonnet-5` all remained **1.0/1.0**.
- The other **71** trial artifacts remain unchanged.

See `repair_evidence.json` for run IDs, artifact digests, task-level hashes and the exact repair provenance.
