# 11 — Operator runbook

## Start

```bash
cp .env.example .env
docker compose up -d --build
```

Wait until:

```bash
curl http://localhost:8080/health
curl http://localhost:8008/patroni
curl http://localhost:8009/patroni
```

One Patroni node should report leader/primary and the other replica.

## Grafana

Open http://localhost:3000 and select folder **Hybrid DB Lab** → **Hybrid Database Lab - Operations**.

## Create experiment

```bash
python scripts/new_experiment.py --scenario primary-failure --repetitions 10
```

Record/commit the generated run ID.

## Execute failure experiment

```bash
python scripts/run_failover.py --run-id EXP-...
```

## Analyze

```bash
pip install -r requirements.txt
python analysis/analyze.py
python analysis/cost_model.py
python -m http.server 8000 -d site
```

## Cleanup

```bash
docker compose down
```

To destroy all local test data:

```bash
docker compose down -v
```

Never run `down -v` against a system containing evidence you still need.
