# 08 — Results protocol

Do not manually type final numbers into this file. Results should be generated from raw evidence.

The pipeline writes:

- `site/data/summary.json` — statistics derived from `MEASURED` experiment result files;
- `site/data/cost.json` — values derived from the `MODELLED` cost assumptions.

When presenting a result, use language such as:

> Under protocol EXP-..., the measured median RTO was X seconds across N repeated runs. The result applies to the documented workload, resource allocation and network conditions and is not a universal property of PostgreSQL, Azure or hybrid architecture.
