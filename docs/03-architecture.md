# 03 — PoC architecture

## Local reproducible lab

```text
                       k6 / pgbench
                            |
                            v
                        Demo API
                            |
                            v
                         HAProxy
                            |
                   primary-only routing
                       /         \
                      /           \
               PostgreSQL 1   PostgreSQL 2
                  Patroni        Patroni
                      \           /
                       \         /
                          etcd

Metrics: API /metrics + db-metrics -> Prometheus -> Grafana
Logs:    API -> Loki -> Grafana
Evidence: experiment runner -> experiments/EXP-*/raw
Analysis: Python -> site/data/*.json -> GitHub Pages
```

## Production mapping

The local two-node topology is a **functional model**, not a production design.

A production mapping would normally include:

- resilient DCS/quorum rather than one etcd node;
- at least two failure domains per active site where required;
- secure private connectivity between sites;
- TLS/mTLS, managed secrets and certificate rotation;
- real backup/restore infrastructure;
- separate management/control plane;
- identity, RBAC and audit controls;
- cloud billing exports and actual on-prem cost allocation;
- explicit split-brain fencing and tested runbooks.

## Switchover versus failover

**Switchover** is planned. Writes are drained, replication catches up, target is promoted, traffic changes, then health is validated.

**Failover** is unplanned. The old primary is unavailable and the HA system promotes an eligible replica according to quorum/lag policy. The failure experiment in this PoC measures the latter.
