# Hybrid Database Decision Lab

A reproducible Proof of Concept for evaluating **On-Premises**, **Cloud-only** and **Hybrid** database architectures before a technology decision.

The lab separates four layers:

1. **Experiment** — repeatable workload + controlled failures.
2. **Observability** — Prometheus metrics, Grafana dashboards and Loki application logs.
3. **Evidence** — immutable per-run raw JSON/log files plus checksums.
4. **Decision layer** — statistical aggregation, cost model and a static GitHub Pages dashboard.

> This project does **not** claim that Hybrid is universally best. It is designed to show which candidate meets a defined set of requirements under defined workloads and failure scenarios.

## Architecture

```text
                   k6 / pgbench
                        |
                        v
                   Demo API
                        |
                        v
                     HAProxy
                        |
              +---------+---------+
              |                   |
          PostgreSQL-1         PostgreSQL-2
          Patroni node         Patroni node
              \                   /
               +------ etcd -----+

             Metrics / Logs / Events
                        |
       +----------------+----------------+
       |                                 |
   Prometheus ------------------------> Grafana
       |                                 ^
   db-metrics                            |
   API /metrics                          Loki

            Raw experiment evidence
                        |
                 Python analysis
                        |
        site/data/{summary,cost}.json
                        |
                 GitHub Pages
```

## Quick start

Requirements: Docker Desktop / Docker Engine with Compose v2, Python 3.11+ and Git.

```bash
cp .env.example .env
docker compose up -d --build
```

Open:

- Demo API: http://localhost:8080/docs
- Grafana: http://localhost:3000 (`admin` / `admin` by default)
- Prometheus: http://localhost:9090
- HAProxy statistics: http://localhost:8404/stats
- Patroni node 1 API: http://localhost:8008/patroni
- Patroni node 2 API: http://localhost:8009/patroni

Verify the database path:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/db
```

## First experiment

Create the pre-registration file **before** running the test:

```bash
python scripts/new_experiment.py --scenario primary-failure --repetitions 10
```

Commit the generated `protocol.yaml` if you want a Git timestamp as preregistration evidence.

Then run one failure test:

```bash
python scripts/run_failover.py --run-id EXP-YYYYMMDD-HHMMSS
```

The runner:

1. detects the current Patroni leader;
2. starts a steady k6 workload;
3. continuously writes numbered RPO probes;
4. kills the primary container;
5. waits for a new leader and successful API writes;
6. calculates measured RTO and acknowledged-write loss;
7. writes raw evidence and SHA-256 checksums;
8. restarts the old node.

Analyze all measured runs:

```bash
python analysis/analyze.py
python analysis/cost_model.py
```

The decision dashboard is served automatically by the `dashboard` container (started with `docker compose up`) at http://localhost:8000. It also exposes `/api/upload` and `/api/ingest` so real on-prem/cloud measurements can be pushed in without a manual `docker compose` run — see the "Daten verbinden" section on the page (token in `.env` → `DASHBOARD_API_TOKEN`).

## Publish to GitHub Pages

The static build (`analyze.py` + `cost_model.py` + `decision.py` → `site/`) is already wired to `.github/workflows/pages.yml`:

```bash
git init                       # if not already a repo
git add .
git commit -m "Initial commit"
gh repo create <name> --public --source=. --remote=origin --push
```

Then in the GitHub repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**. The workflow runs on every push to `main` and regenerates `site/data/*.json` from whatever is in `experiments/` at that commit — no local build step needed. The `dashboard` container (upload/API ingestion, live localhost links) only runs locally; on GitHub Pages the page detects this and falls back to a static, pre-computed snapshot automatically.

## Operating modes represented by the PoC

- **ON_PREM_ONLY** — application and primary database reside in the local site.
- **CLOUD_ONLY** — application and primary database reside in the cloud site.
- **HYBRID** — one site is primary, the other is a synchronized standby; controlled switchover changes the active site.

The local lab emulates the two sites. The optional `infra/terraform/azure` directory provides a small Azure VM skeleton for a real-cloud validation run. A simulated WAN must always be labelled as simulation in results.

## Scientific controls

The project includes:

- preregistered protocol per experiment;
- requirements and explicit pass/fail gates;
- fixed workload definitions;
- repeated runs;
- raw evidence kept separate from derived statistics;
- provenance labels (`MEASURED`, `SIMULATED`, `MODELLED`);
- median / IQR / bootstrap confidence interval;
- decision matrix only after mandatory gates;
- sensitivity analysis for decision weights;
- limitations section.

See `docs/` for the complete PoC documentation.

## Important limitations

This repository is a **PoC**, not a production HA reference architecture. In particular:

- it uses a single etcd node for simplicity; production Patroni requires a resilient DCS/quorum design;
- Docker networks are not equivalent to a real WAN;
- a local container failure does not reproduce a full datacenter outage;
- cost values in `cost/assumptions.yaml` are examples until replaced by sourced real values;
- public GitHub Pages must contain only aggregated, non-sensitive results.

## Repository map

```text
api/                    synthetic demo-service API
analysis/               statistics + cost calculations
cost/                   versioned cost assumptions
dashboard/              local dashboard server (static site + upload/ingest API)
experiments/            preregistration + raw evidence
infra/patroni/           PostgreSQL/Patroni image and configs
infra/terraform/azure/   optional real-cloud validation skeleton
observability/           Prometheus, Grafana, Loki configuration
scripts/                 experiment orchestration
site/                    static GitHub Pages decision dashboard
workload/k6/             end-to-end workload
workload/pgbench/        database workload
.github/workflows/       validation + Pages deployment
```
