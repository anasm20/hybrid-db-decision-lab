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
topology:
  database_site: on-prem
  app_hosting: {app_hosting}
  server_model: {server_model}
workload:
  tool: k6
  virtual_users: {vus}
  duration: {duration}
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
p.add_argument('--vus', type=int, default=25, help='concurrent virtual users (simulated simultaneous access)')
p.add_argument('--duration', default='3m', help='k6 workload duration, e.g. 1m/3m/10m')
p.add_argument('--server-model', choices=['small','medium','large'], default='medium', help='On-Prem server size applied to the DB nodes')
p.add_argument('--app-hosting', default='on-prem', help='comma-separated labels, e.g. aws,azure for multi-cloud (DB always stays On-Prem)')
a=p.parse_args()
run_id='EXP-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
root=Path(__file__).resolve().parents[1]/'experiments'/run_id
(root/'raw').mkdir(parents=True)
(root/'processed').mkdir()
created=datetime.now(timezone.utc).isoformat()
app_hosting=[x.strip() for x in a.app_hosting.split(',') if x.strip()]
(root/'protocol.yaml').write_text(TEMPLATE.format(run_id=run_id,created=created,scenario=a.scenario,repetitions=a.repetitions,vus=a.vus,duration=a.duration,server_model=a.server_model,app_hosting=app_hosting),encoding='utf-8')
(root/'metadata.json').write_text('{\n  "experiment_id": "'+run_id+'",\n  "provenance": "MEASURED",\n  "status": "PREREGISTERED"\n}\n',encoding='utf-8')
print(run_id)
print(root)
