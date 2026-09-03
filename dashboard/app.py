import hashlib
import json
import os
import re
import secrets
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(os.getenv("HOST_PROJECT_DIR", "/workspace"))
EXPERIMENTS = ROOT / "experiments"
SITE = ROOT / "site"
API_TOKEN = os.getenv("DASHBOARD_API_TOKEN", "")
SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
SERVER_MODELS = {"small", "medium", "large"}
DURATIONS = {"1m", "3m", "5m", "10m"}

# Env overrides so scripts/run_failover.py — normally executed on the host, where it
# reaches services via the docker-compose port mappings on localhost — resolves the
# same services by their Docker network name when spawned from inside this container.
SCENARIO_RUN_ENV = {
    "PATRONI1_URL": "http://postgres1:8008/patroni",
    "PATRONI2_URL": "http://postgres2:8008/patroni",
    "DEMO_API_URL": "http://demo-api:8080",
    "LAG_METRICS_URL": "http://db-metrics:9105/metrics",
    "DASHBOARD_URL": "http://localhost:8000",
}

# Terminal event kinds that mark a run as no longer active/live.
TERMINAL_EVENTS = {"service_write_recovered", "recovery_timeout", "experiment_completed"}
MAX_EVENTS = 2000

app = FastAPI(title="Decision Lab Dashboard")

_events_lock = threading.Lock()
EVENTS: list[dict] = []
ACTIVE_RUNS: dict[str, dict] = {}


def require_token(authorization: Optional[str]):
    if not API_TOKEN:
        raise HTTPException(500, "DASHBOARD_API_TOKEN not configured on server")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    if authorization.split(" ", 1)[1] != API_TOKEN:
        raise HTTPException(401, "invalid token")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def store_result(payload: dict) -> dict:
    experiment_id = str(payload.get("experiment_id") or f"EXT-{int(time.time())}")
    if not SAFE_ID.match(experiment_id):
        raise HTTPException(400, "experiment_id must match ^[A-Za-z0-9_.-]{1,80}$")
    payload["experiment_id"] = experiment_id
    payload.setdefault("provenance", "MEASURED")
    if payload["provenance"] not in ("MEASURED", "SIMULATED"):
        raise HTTPException(400, "provenance must be MEASURED or SIMULATED")
    payload.setdefault("finished_at", datetime.now(timezone.utc).isoformat())

    exp_dir = EXPERIMENTS / experiment_id
    raw_dir = exp_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "metadata.json").write_text(json.dumps({
        "experiment_id": experiment_id,
        "source": "dashboard-api",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETED",
    }, indent=2), encoding="utf-8")
    (raw_dir / "result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    checks = []
    for f in sorted(raw_dir.glob("*")):
        if f.is_file():
            checks.append(f"{sha256(f)}  raw/{f.name}")
    (exp_dir / "checksums.sha256").write_text("\n".join(checks) + "\n", encoding="utf-8")

    proc = subprocess.run(["python3", "analysis/analyze.py"], cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise HTTPException(500, f"stored but analyze.py failed: {proc.stderr[-2000:]}")
    return payload


class IngestPayload(BaseModel):
    experiment_id: Optional[str] = None
    provenance: Optional[str] = "MEASURED"
    scenario: Optional[str] = "external"
    initial_primary: Optional[str] = None
    promoted_primary: Optional[str] = None
    rto_seconds: Optional[float] = None
    acknowledged_write_loss: Optional[int] = 0
    replication_lag_seconds_max: Optional[float] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    workload: Optional[dict] = None

    class Config:
        extra = "allow"


@app.post("/api/ingest")
def ingest(payload: IngestPayload, authorization: Optional[str] = Header(None)):
    require_token(authorization)
    stored = store_result(payload.dict(exclude_none=True))
    return {"stored": True, "experiment_id": stored["experiment_id"]}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    require_token(authorization)
    raw = await file.read()
    if len(raw) > 2_000_000:
        raise HTTPException(413, "file too large (max 2MB)")
    try:
        payload = json.loads(raw)
    except Exception:
        raise HTTPException(400, "file must be valid JSON")
    if not isinstance(payload, dict):
        raise HTTPException(400, "JSON root must be an object")
    stored = store_result(payload)
    return {"stored": True, "experiment_id": stored["experiment_id"]}


class RunEvent(BaseModel):
    run_id: str
    event: str
    at: Optional[str] = None
    epoch: Optional[float] = None

    class Config:
        extra = "allow"


@app.post("/api/events")
def push_event(payload: RunEvent, authorization: Optional[str] = Header(None)):
    require_token(authorization)
    if not SAFE_ID.match(payload.run_id):
        raise HTTPException(400, "run_id must match ^[A-Za-z0-9_.-]{1,80}$")
    row = payload.dict(exclude_none=True)
    row.setdefault("at", datetime.now(timezone.utc).isoformat())
    row.setdefault("epoch", time.time())
    with _events_lock:
        EVENTS.append(row)
        if len(EVENTS) > MAX_EVENTS:
            del EVENTS[: len(EVENTS) - MAX_EVENTS]
        if row["event"] == "experiment_started":
            ACTIVE_RUNS[payload.run_id] = {"started_epoch": row["epoch"]}
        elif row["event"] in TERMINAL_EVENTS:
            ACTIVE_RUNS.pop(payload.run_id, None)
    return {"stored": True}


@app.get("/api/events")
def get_events(run_id: Optional[str] = None, since_epoch: Optional[float] = None):
    with _events_lock:
        rows = list(EVENTS)
        active = list(ACTIVE_RUNS.keys())
    if run_id:
        rows = [r for r in rows if r.get("run_id") == run_id]
    if since_epoch is not None:
        rows = [r for r in rows if r.get("epoch", 0) > since_epoch]
    return {"active_run_ids": active, "events": rows[-500:]}


class ScenarioRequest(BaseModel):
    server_model: str = "medium"
    vus: int = 25
    duration: str = "3m"
    app_hosting: list = []


@app.post("/api/run-scenario")
def run_scenario(payload: ScenarioRequest, authorization: Optional[str] = Header(None)):
    require_token(authorization)
    if payload.server_model not in SERVER_MODELS:
        raise HTTPException(400, f"server_model must be one of {sorted(SERVER_MODELS)}")
    if payload.duration not in DURATIONS:
        raise HTTPException(400, f"duration must be one of {sorted(DURATIONS)}")
    if not (1 <= payload.vus <= 1000):
        raise HTTPException(400, "vus must be between 1 and 1000")

    with _events_lock:
        if ACTIVE_RUNS:
            raise HTTPException(409, f"a run is already active: {list(ACTIVE_RUNS.keys())}")

    app_hosting = ",".join(str(x) for x in payload.app_hosting) if payload.app_hosting else "on-prem"

    new_exp = subprocess.run(
        ["python3", "scripts/new_experiment.py", "--scenario", "primary-failure", "--repetitions", "1",
         "--vus", str(payload.vus), "--duration", payload.duration,
         "--server-model", payload.server_model, "--app-hosting", app_hosting],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if new_exp.returncode != 0:
        raise HTTPException(500, f"new_experiment.py failed: {new_exp.stderr[-1500:]}")
    run_id = (new_exp.stdout.strip().splitlines() or [""])[0].strip()
    if not SAFE_ID.match(run_id):
        raise HTTPException(500, f"unexpected run id from new_experiment.py: {run_id!r}")

    env = os.environ.copy()
    env.update(SCENARIO_RUN_ENV)
    log = open(EXPERIMENTS / run_id / "raw" / "runner.log", "w")
    subprocess.Popen(
        ["python3", "scripts/run_failover.py", "--run-id", run_id,
         "--vus", str(payload.vus), "--duration", payload.duration,
         "--server-model", payload.server_model, "--app-hosting", app_hosting],
        cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    return {"started": True, "run_id": run_id}


@app.get("/api/status")
def status():
    count = len([p for p in EXPERIMENTS.glob("*") if (p / "raw" / "result.json").exists()]) if EXPERIMENTS.exists() else 0
    with _events_lock:
        active = list(ACTIVE_RUNS.keys())
    return {"token_configured": bool(API_TOKEN), "experiment_count": count, "active_run_ids": active}


@app.post("/api/simulate")
def simulate(authorization: Optional[str] = Header(None)):
    """Create a labelled demo result without adding it to measured evidence."""
    require_token(authorization)
    rto = round(8 + secrets.randbelow(170) / 10, 1)
    lag = round(0.2 + secrets.randbelow(39) / 10, 1)
    error_rate = round(0.002 + secrets.randbelow(39) / 1000, 3)
    p95 = 120 + secrets.randbelow(361)
    return {
        "experiment_id": f"SIM-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "provenance": "SIMULATED",
        "scenario": "primary-failure-demo",
        "initial_primary": "postgres1",
        "promoted_primary": "postgres2",
        "rto_seconds": rto,
        "acknowledged_write_loss": secrets.randbelow(2),
        "replication_lag_seconds_max": lag,
        "workload": {
            "p95_ms": p95,
            "p99_ms": p95 + 80 + secrets.randbelow(241),
            "error_rate": error_rate,
            "throughput_rps": round(20 + secrets.randbelow(401) / 10, 1),
        },
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


app.mount("/", StaticFiles(directory=str(SITE), html=True), name="site")
