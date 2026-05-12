# benchmarks/

One subdirectory per benchmark, self-contained:

```
benchmarks/<name>/
├── README.md                  # submission notes for this benchmark
├── schema/
│   ├── submission-v1.json     # JSON Schema for submission.json
│   ├── known-versions.txt     # accepted dataset versions (one per line)
│   └── README.md              # versioning policy
└── submissions/
    └── <YYYY-MM-DD>-<slug>/   # one dir per accepted submission
```

## Adding a new benchmark

1. Pick a benchmark slug (`my-bench`). Create `benchmarks/my-bench/{schema,submissions}/` and the four files above.
2. Write `schema/submission-v1.json` covering:
   - The **cross-benchmark envelope** documented in the chi-bench [submission packet contract](https://github.com/actava-ai/chi-bench/blob/main/docs/submission-packet.md) (fields `schema`, `submission.*`, `dataset.*`, `provenance.*` — required), and
   - Your benchmark-specific `results.*` shape.
3. List your benchmark's accepted dataset versions in `schema/known-versions.txt`, one per line.
4. Document any benchmark-specific notes in your `README.md` — how to produce a packet, how to inspect results, links to your producer repo.

No leaderboard-side code changes are needed. `scripts/submit.py` reads `submission.json:dataset.name` to route packets into the right subtree, and `.github/scripts/validate_submission.py` resolves your schema from the manifest's `schema:` field.
