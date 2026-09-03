# 06 — Observability

## Grafana dashboard

The dashboard is provisioned automatically from:

`observability/grafana/dashboards/hybrid-db-lab.json`

It contains:

- requests per second;
- API p95 latency;
- HTTP 5xx error rate;
- database primary role per node;
- replication replay lag;
- database connection count;
- node queryability;
- transaction counter;
- DB metric collection errors;
- Demo API logs from Loki.

## Metric provenance

Application metrics are emitted by the synthetic API via Prometheus client instrumentation. Database metrics are produced by the custom `db-metrics` exporter using PostgreSQL statistics plus Patroni REST role state.

## Recommended production additions

- OS/node exporter;
- storage latency/IOPS from the hypervisor/cloud provider;
- PostgreSQL wait-event breakdown;
- database size/WAL volume;
- backup success and backup age;
- OpenTelemetry traces for request-to-query attribution;
- Grafana annotations for experiment events;
- alerting tied to SLOs rather than dashboard-only monitoring.
