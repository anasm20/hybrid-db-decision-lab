#!/usr/bin/env python3
import json, math, random, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROBE_INTERVAL_SECONDS=0.2

def bootstrap_ci(values, rounds=5000, alpha=.05):
    if not values: return [None,None]
    rng=random.Random(20260903)
    medians=[]
    for _ in range(rounds): medians.append(statistics.median(rng.choices(values,k=len(values))))
    medians.sort(); return [medians[int(alpha/2*rounds)],medians[int((1-alpha/2)*rounds)-1]]

def stats(values):
    return {"median":statistics.median(values) if values else None,"max":max(values) if values else None}

def load_k6_workload(run_dir):
    p=run_dir/'raw'/'k6-summary.json'
    if not p.exists(): return {}
    try: d=json.loads(p.read_text())
    except Exception: return {}
    m=d.get('metrics',{})
    # k6's --summary-export nests trend/rate stats under a "values" key on some
    # versions and puts them directly on the metric object on others (e.g. 0.57.x)
    # — support both. http_req_failed's rate is called "rate" in the nested form
    # and "value" in the flat form.
    dur=m.get('http_req_duration',{}); dur=dur.get('values',dur)
    failed=m.get('http_req_failed',{}); failed=failed.get('values',failed)
    reqs=m.get('http_reqs',{}); reqs=reqs.get('values',reqs)
    return {
        "p95_ms":dur.get('p(95)'),
        "p99_ms":dur.get('p(99)'),
        "error_rate":failed.get('rate', failed.get('value')),
        "throughput_rps":reqs.get('rate'),
    }

def load_workload(run_dir, result):
    # k6 raw evidence takes precedence; explicitly supplied values (e.g. from an
    # external on-prem/cloud system pushed via the dashboard API) fill any gaps.
    merged=load_k6_workload(run_dir)
    provided=result.get('workload') or {}
    for k,v in provided.items():
        if v is not None: merged[k]=v
    return merged

all_runs=[]
for p in sorted((ROOT/'experiments').glob('*/raw/result.json')):
    d=json.loads(p.read_text())
    d['workload']=load_workload(p.parents[1], d)
    all_runs.append(d)

# SIMULATED/demo runs are shown in the runs list for visibility but never feed
# the aggregate KPI statistics or gate checks — those stay strictly MEASURED-only.
runs=[x for x in all_runs if x.get('provenance')=='MEASURED']

rto=[float(x['rto_seconds']) for x in runs if x.get('rto_seconds') is not None]
loss=[int(x.get('acknowledged_write_loss',0)) for x in runs]
lag=[float(x['replication_lag_seconds_max']) for x in runs if x.get('replication_lag_seconds_max') is not None]
err=[float(x['workload']['error_rate']) for x in runs if x.get('workload',{}).get('error_rate') is not None]
p95=[float(x['workload']['p95_ms']) for x in runs if x.get('workload',{}).get('p95_ms') is not None]
p99=[float(x['workload']['p99_ms']) for x in runs if x.get('workload',{}).get('p99_ms') is not None]
tput=[float(x['workload']['throughput_rps']) for x in runs if x.get('workload',{}).get('throughput_rps') is not None]

summary={
 "provenance":"DERIVED_FROM_MEASURED","run_count":len(runs),
 "rpo":{
   "acknowledged_write_loss_probes":{"median":statistics.median(loss) if loss else None,"max":max(loss) if loss else None},
   "probe_interval_seconds":PROBE_INTERVAL_SECONDS,
   "estimated_seconds":{
     "median":(statistics.median(loss)*PROBE_INTERVAL_SECONDS) if loss else None,
     "max":(max(loss)*PROBE_INTERVAL_SECONDS) if loss else None,
   },
 },
 "rto_seconds": {"median":statistics.median(rto) if rto else None,"mean":statistics.mean(rto) if rto else None,"min":min(rto) if rto else None,"max":max(rto) if rto else None,"bootstrap_95_ci_median":bootstrap_ci(rto) if rto else [None,None]},
 "error_rate": stats(err),
 "latency_ms": {"p95":stats(p95),"p99":stats(p99)},
 "replication_lag_seconds": stats(lag),
 "throughput_rps": stats(tput),
 "runs": all_runs,
}
out=ROOT/'site/data/summary.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(out)
