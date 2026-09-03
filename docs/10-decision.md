# 10 — Decision framework

The decision is intentionally downstream of the experiments.

## Example dimensions

| Dimension | Example weight |
|---|---:|
| Resilience | 25% |
| Performance | 20% |
| Data integrity | 15% |
| Cost | 15% |
| Sovereignty | 10% |
| Portability | 10% |
| Operations | 5% |

Weights are assumptions, not measurements.

## Mandatory gates

Before scoring, reject a candidate when an agreed mandatory requirement fails, for example:

- RPO exceeds the maximum acceptable loss;
- restore test fails;
- security/data residency requirement is not met;
- RTO exceeds the service requirement.

## Sensitivity analysis

Vary each important weight across a plausible range and record where the winning candidate changes. The output should say, for example:

> Hybrid is preferred under the base weights, but Cloud-only becomes preferred when cost exceeds 48% of total decision weight.

That is more informative than an unexplained single score such as 89/100.
