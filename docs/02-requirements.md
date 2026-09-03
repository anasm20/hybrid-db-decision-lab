# 02 — Requirements and gates

Requirements must be written **before** collecting comparative results.

| ID | Requirement | Metric | Example gate |
|---|---|---|---|
| NFR-P01 | Interactive performance | API p95 | `< 500 ms` |
| NFR-P02 | Tail performance | API p99 | `< 1000 ms` |
| NFR-R01 | Recovery time | measured RTO | `< 30 s` |
| NFR-R02 | Data loss | acknowledged-write loss / RPO | `0` for this PoC |
| NFR-A01 | Availability under baseline | error rate | `< 1%` |
| NFR-D01 | Data integrity | duplicate/lost committed records | `0` |
| NFR-O01 | Observability | metrics + logs available | required |
| NFR-X01 | Portability | same API workload deployable in both sites | required |
| NFR-C01 | Cost transparency | versioned assumptions/source | required |

## Decision rule

1. Apply mandatory gates first.
2. Exclude candidates that fail a mandatory gate.
3. Compare remaining candidates using normalized metrics.
4. Apply a declared decision weighting.
5. Perform sensitivity analysis by varying the weights.

A low cost cannot compensate for a failed restore or unacceptable data loss.
