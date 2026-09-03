# 07 — Cost model

Cost is a model unless it comes from an invoice/billing export. The lab therefore keeps cost provenance separate from performance provenance.

## On-Prem model

Example components:

- compute/storage/network CAPEX amortized over a declared lifetime;
- electricity;
- datacenter/facility allocation;
- software/support licenses;
- backup;
- operations labour.

## Cloud model

Example components:

- compute/database service;
- storage and IOPS if billed separately;
- backup;
- network egress/private connectivity;
- support;
- operations labour.

## Hybrid model

Hybrid adds both sides plus shared tooling/connectivity. It should not be made artificially cheap by omitting duplicate capacity.

`cost/assumptions.yaml` contains **example values only** and is marked `MODELLED`.

## Useful normalized metrics

- EUR per month;
- EUR per 1 million successful requests;
- EUR per 1 million committed transactions;
- 3/5-year TCO;
- cost at baseline and peak utilization.

The cost model should be rerun with low/base/high assumptions and included in sensitivity analysis.
