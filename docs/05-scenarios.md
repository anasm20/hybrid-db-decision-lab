# 05 — Scenario catalogue

| ID | Scenario | Primary evidence |
|---|---|---|
| S0 | Baseline steady workload | p50/p95/p99, RPS/TPS, errors |
| S1 | Saturation / peak load | capacity knee, queueing, errors |
| S2 | Database primary failure | RTO, lost acknowledged writes, error burst |
| S3 | Replica failure | availability, degraded redundancy |
| S4 | WAN latency | latency distribution, replication lag |
| S5 | Packet loss | errors, retries, replication behavior |
| S6 | Complete WAN loss | site autonomy, recovery behavior |
| S7 | Site failure | service availability, DR RTO/RPO |
| S8 | Backup + restore | measured restore time, consistency |
| S9 | Planned switchover | controlled RTO/RPO, validation |
| S10 | Scale-out / scale-up | time-to-capacity, cost delta |
| S11 | Exit / portability | effort, downtime, data export/import |

## Initial PoC scope

The repository automates S2 and provides workload/monitoring foundations for S0/S1. Other scenarios should be added one at a time so that evidence remains interpretable.
