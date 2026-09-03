# 13 — Primary technical sources

Use primary vendor/standards documentation wherever possible. These links are the baseline references for the PoC; pin the accessed date in any formal report.

## Method and quality

- NIST SP 500-307 — Cloud Computing Service Metrics Description: https://www.nist.gov/publications/cloud-computing-service-metrics-description
- ISO/IEC 25010:2023 — Product quality model: https://www.iso.org/standard/78176.html

## PostgreSQL and HA

- PostgreSQL pgbench: https://www.postgresql.org/docs/current/pgbench.html
- PostgreSQL monitoring statistics: https://www.postgresql.org/docs/current/monitoring-stats.html
- PostgreSQL streaming replication: https://www.postgresql.org/docs/current/warm-standby.html
- Patroni documentation: https://patroni.readthedocs.io/
- Patroni replication modes: https://patroni.readthedocs.io/en/latest/replication_modes.html

## Load testing and observability

- Grafana k6 thresholds: https://grafana.com/docs/k6/latest/using-k6/thresholds/
- Prometheus exporters/integrations: https://prometheus.io/docs/instrumenting/exporters/
- Grafana provisioning: https://grafana.com/docs/grafana/latest/administration/provisioning/
- Grafana Loki: https://grafana.com/docs/loki/latest/
- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/

## Cloud / cost

- Azure Retail Prices API: https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices
- Azure Cost Management Query: https://learn.microsoft.com/rest/api/cost-management/query/usage
- AWS Price List API: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html
- Google Cloud Billing Catalog API: https://cloud.google.com/billing/docs/reference/rest/v1/services.skus/list
- FinOps FOCUS specification: https://focus.finops.org/

## Benchmark extension

- HammerDB documentation: https://www.hammerdb.com/docs/

## Vienna public data for non-personal test datasets

- City of Vienna Open Government Data: https://digitales.wien.gv.at/open-data/
- Austrian Open Data catalogue: https://www.data.gv.at/

Do not use internal municipal logs or personal data in a public repository. Public OGD can enrich read/search/ETL scenarios, but the initial OLTP correctness tests should use deterministic synthetic data.
