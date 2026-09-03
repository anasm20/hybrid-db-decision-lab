# 04 — Methodology

## Reproducibility principles

Every comparable experiment should record:

- experiment ID;
- Git commit;
- software versions;
- CPU/RAM/storage allocation;
- database size and seed;
- workload definition;
- warm-up and measurement duration;
- network conditions;
- failure injection time and method;
- all success/failure thresholds;
- provenance: `MEASURED`, `SIMULATED`, `MODELLED` or `ASSESSED`.

## Preregistration

Run `scripts/new_experiment.py` before a test. The generated `protocol.yaml` contains the hypothesis, scenario, workload and gates. Commit it before execution when using Git timestamps as evidence that criteria were not chosen after seeing the result.

## Repetition

Do not infer an architecture decision from a single run. Use repeated runs and report distributions. For the initial PoC, ten runs per candidate/scenario are a pragmatic minimum for demonstrating the method; production evaluation should determine sample size from expected variance and practical effect thresholds.

## Statistics

The included analyzer reports median, mean, range and a deterministic bootstrap 95% confidence interval for the median RTO. Extend it with IQR, Mann-Whitney U and Cliff's Delta when comparing two candidate distributions.

Statistical significance must not be confused with practical relevance. Define a minimum practically important difference before interpreting a small latency difference as meaningful.

## Fair comparison

The same workload and test client must be used for all candidates. Resource normalization must be declared. A 4-vCPU local VM is not directly comparable with a 32-vCPU cloud database without an explicit capacity/cost normalization.

## Simulation versus validation

Local network impairment can test protocol behavior, but it must be labelled `SIMULATED`. A real-cloud validation run should repeat a subset of representative tests and be labelled `MEASURED` with the actual region/SKU/network path recorded.
