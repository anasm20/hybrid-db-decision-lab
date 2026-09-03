#!/usr/bin/env python3
import argparse, hashlib, json, os, subprocess, threading, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT=Path(__file__).resolve().parents[1]
PATRONI={"postgres1":"http://localhost:8008/patroni","postgres2":"http://localhost:8009/patroni"}
API="http://localhost:8080"

def load_dotenv(path):
    if not path.exists(): return
    for line in path.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1)
        os.environ.setdefault(k.strip(),v.strip())
load_dotenv(ROOT/'.env')

DASHBOARD_URL=os.getenv('DASHBOARD_URL','http://localhost:8000')
DASHBOARD_TOKEN=os.getenv('DASHBOARD_API_TOKEN','')

def now(): return datetime.now(timezone.utc).isoformat()

def get_json(url, timeout=2):
    with urlopen(url,timeout=timeout) as r: return json.loads(r.read().decode())

def post(url):
    req=Request(url,method='POST',data=b'{}',headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=2) as r: return json.loads(r.read().decode())

def post_json(url, payload, token=None, timeout=1.5):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']=f'Bearer {token}'
    req=Request(url,method='POST',data=json.dumps(payload).encode(),headers=headers)
    with urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode())

def push_live_event(run_id, row):
    # Best-effort: the live dashboard panel is a convenience, never block the experiment on it.
    if not DASHBOARD_TOKEN: return
    try: post_json(f'{DASHBOARD_URL}/api/events', {**row, 'run_id':run_id}, token=DASHBOARD_TOKEN)
    except Exception: pass

def leader():
    for name,url in PATRONI.items():
        try:
            d=get_json(url)
            if d.get('role') in ('master','primary') and d.get('state')=='running': return name
        except Exception: pass
    return None

def api_ok():
    try: return get_json(API+'/health',1).get('status')=='ok'
    except Exception: return False

def replication_lag_snapshot():
    try:
        text = urlopen('http://localhost:9105/metrics', timeout=1).read().decode()
    except Exception:
        return {}
    lag = {}
    for line in text.splitlines():
        if line.startswith('db_replication_lag_seconds{'):
            try:
                node = line.split('node="')[1].split('"')[0]
                val = float(line.rsplit(' ', 1)[1])
                lag[node] = val
            except Exception:
                pass
    return lag

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); p.add_argument('--warmup',type=int,default=60); p.add_argument('--timeout',type=int,default=90)
a=p.parse_args()
exp=ROOT/'experiments'/a.run_id; raw=exp/'raw'; raw.mkdir(parents=True,exist_ok=True)
if not (exp/'protocol.yaml').exists(): raise SystemExit('protocol.yaml missing: create/preregister experiment first')

events=[]
def event(kind,**kw):
    row={"at":now(),"epoch":time.time(),"event":kind,**kw}; events.append(row); print(row)
    push_live_event(a.run_id,row)

primary=leader()
if not primary: raise SystemExit('No Patroni leader detected. Start docker compose first.')
event('experiment_started',initial_primary=primary)

stop_probe=False; ack=[]
def probe_loop():
    seq=int(time.time()*1000)
    while not stop_probe:
        seq+=1
        try:
            r=post(f'{API}/rpo/probe/{seq}')
            ack.append((seq,time.time()))
        except Exception: pass
        time.sleep(.2)
pt=threading.Thread(target=probe_loop,daemon=True); pt.start()

lag_samples=[]
def lag_loop():
    while not stop_probe:
        snap=replication_lag_snapshot()
        if snap: lag_samples.append(max(snap.values()))
        time.sleep(1)
lt=threading.Thread(target=lag_loop,daemon=True); lt.start()

k6out=raw/'k6-summary.json'
env=os.environ.copy(); env['RUN_ID']=a.run_id
k6cmd=['docker','compose','run','--rm','-e',f'RUN_ID={a.run_id}','-e','DURATION=3m','k6','run','--summary-export',f'/experiments/{a.run_id}/raw/k6-summary.json','/scripts/steady.js']
k6=subprocess.Popen(k6cmd,cwd=ROOT,env=env,stdout=open(raw/'k6.log','w'),stderr=subprocess.STDOUT)

time.sleep(a.warmup)
primary=leader() or primary
event('failure_injected',target=primary)
t0=time.time()
subprocess.run(['docker','compose','kill',primary],cwd=ROOT,check=True)

new_primary=None
first_healthy=None
deadline=t0+a.timeout
while time.time()<deadline:
    lp=leader()
    if lp and lp!=primary and not new_primary:
        new_primary=lp; event('new_primary_detected',node=lp,elapsed_seconds=time.time()-t0)
    if new_primary and api_ok():
        try:
            seq=int(time.time()*1000)
            post(f'{API}/rpo/probe/{seq}')
            first_healthy=time.time(); event('service_write_recovered',elapsed_seconds=first_healthy-t0); break
        except Exception: pass
    time.sleep(.5)

stop_probe=True; pt.join(timeout=2); lt.join(timeout=2)
if first_healthy is None: event('recovery_timeout')
# Give any client request time to complete, then inspect promoted database.
time.sleep(1)
try: max_seq=int(get_json(API+'/rpo/max')['max_sequence'])
except Exception: max_seq=0
last_ack=max([x[0] for x in ack],default=0)
lost=max(0,last_ack-max_seq)
rto=(first_healthy-t0) if first_healthy else None
result={
 "experiment_id":a.run_id,"provenance":"MEASURED","scenario":"primary-failure",
 "initial_primary":primary,"promoted_primary":new_primary,"rto_seconds":rto,
 "last_acknowledged_probe":last_ack,"max_probe_after_recovery":max_seq,
 "acknowledged_write_loss":lost,"replication_lag_seconds_max":max(lag_samples) if lag_samples else None,
 "started_at":events[0]['at'],"finished_at":now()
}
(raw/'events.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
(raw/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
event('experiment_completed',result=result)
# Restart failed node and leave it to rejoin as replica.
subprocess.run(['docker','compose','start',primary],cwd=ROOT,check=False)
k6.wait(timeout=180)
checks=[]
for f in sorted(raw.glob('*')):
    if f.is_file(): checks.append(f'{sha256(f)}  raw/{f.name}')
(exp/'checksums.sha256').write_text('\n'.join(checks)+'\n',encoding='utf-8')
meta=exp/'metadata.json'; md=json.loads(meta.read_text()); md.update({"status":"COMPLETED","completed_at":now(),"initial_primary":primary,"promoted_primary":new_primary}); meta.write_text(json.dumps(md,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
