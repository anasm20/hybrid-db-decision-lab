#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE = """experiment_id: {run_id}
created_at_utc: {created}
provenance: MEASURED
scenario: {scenario}
research_question: >
  Which architecture meets the preregistered performance, resilience and data-integrity requirements under this scenario?
hypothesis: >
  The candidate will recover within the RTO gate while keeping acknowledged-write loss within the RPO gate.
repetitions_planned: {repetitions}
primary_metric: rto_seconds
success_criteria:
  rto_seconds: {{operator: "<", value: 30}}
  acknowledged_write_loss: {{operator: "<=", value: 0}}
  p95_latency_ms: {{operator: "<", value: 500}}
  error_rate: {{operator: "<", value: 0.05}}
workload:
  tool: k6
  virtual_users: 25
  duration: 3m
  warmup_seconds: 30
failure_injection:
  type: kill_current_database_primary
  inject_after_seconds: 60
controlled_variables:
  database: PostgreSQL 16
  ha: Patroni
  routing: HAProxy
  same_workload_across_candidates: true
limitations:
  - Local Docker networking is an emulation, not a measured public-cloud WAN.
  - Single-node etcd is used only for the PoC and is not production HA.
"""

p=argparse.ArgumentParser()
p.add_argument('--scenario', default='primary-failure')
p.add_argument('--repetitions', type=int, default=10)
a=p.parse_args()
run_id='EXP-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
root=Path(__file__).resolve().parents[1]/'experiments'/run_id
(root/'raw').mkdir(parents=True)
(root/'processed').mkdir()
created=datetime.now(timezone.utc).isoformat()
(root/'protocol.yaml').write_text(TEMPLATE.format(run_id=run_id,created=created,scenario=a.scenario,repetitions=a.repetitions),encoding='utf-8')
(root/'metadata.json').write_text('{\n  "experiment_id": "'+run_id+'",\n  "provenance": "MEASURED",\n  "status": "PREREGISTERED"\n}\n',encoding='utf-8')
print(run_id)
print(root)
