import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone

import httpx
import psycopg
from fastapi import FastAPI, HTTPException, Request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@localhost:5432/citylab")
LOKI_URL = os.getenv("LOKI_URL", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

app = FastAPI(title="Demo Service Simulator", version="1.0.0")
log = logging.getLogger("demo-api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REQS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LAT = Histogram(
    "http_request_duration_seconds",
    "Request duration",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1, 2, 5),
)
DB_ERRORS = Counter("db_errors_total", "Database operation errors", ["operation"])


def loki(level: str, message: str, **fields):
    payload = {"level": level, "message": message, "environment": ENVIRONMENT, **fields}
    log.info(json.dumps(payload, default=str))
    if not LOKI_URL:
        return
    try:
        ns = str(int(time.time() * 1_000_000_000))
        body = {
            "streams": [{
                "stream": {"app": "demo-api", "environment": ENVIRONMENT, "level": level},
                "values": [[ns, json.dumps(payload, default=str)]],
            }]
        }
        httpx.post(f"{LOKI_URL}/loki/api/v1/push", json=body, timeout=0.5)
    except Exception:
        pass


@contextmanager
def db():
    conn = psycopg.connect(DATABASE_URL, connect_timeout=3, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def ensure_schema():
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            with db() as conn:
                with conn.cursor() as cur:
                    cur.execute("CREATE TABLE IF NOT EXISTS records (id BIGSERIAL PRIMARY KEY, external_id TEXT UNIQUE NOT NULL, district INT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())")
                    cur.execute("CREATE TABLE IF NOT EXISTS applications (id BIGSERIAL PRIMARY KEY, record_id BIGINT REFERENCES records(id), status TEXT NOT NULL, payload JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now())")
                    cur.execute("CREATE TABLE IF NOT EXISTS rpo_probe (sequence BIGINT PRIMARY KEY, committed_at TIMESTAMPTZ NOT NULL DEFAULT now())")
            loki("info", "schema ready")
            return
        except Exception as exc:
            log.warning("waiting for database: %s", exc)
            time.sleep(2)
    raise RuntimeError("database did not become ready")


@app.on_event("startup")
def startup():
    ensure_schema()


@app.middleware("http")
async def metrics(request: Request, call_next):
    start = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        REQS.labels(request.method, request.url.path, status).inc()
        LAT.labels(request.method, request.url.path).observe(time.perf_counter() - start)


@app.get("/metrics")
def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    try:
        with db() as conn:
            value = conn.execute("SELECT 1").fetchone()[0]
        return {"status": "ok", "db": value, "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        DB_ERRORS.labels("health").inc()
        raise HTTPException(503, detail=str(exc))


@app.get("/db")
def database_info():
    try:
        with db() as conn:
            row = conn.execute("SELECT inet_server_addr()::text, inet_server_port(), pg_is_in_recovery(), current_database(), now()").fetchone()
        return {"server_addr": row[0], "server_port": row[1], "is_replica": row[2], "database": row[3], "timestamp": row[4]}
    except Exception as exc:
        DB_ERRORS.labels("db_info").inc()
        raise HTTPException(503, detail=str(exc))


@app.post("/records")
def create_record(payload: dict):
    external_id = payload.get("external_id")
    district = int(payload.get("district", 1))
    if not external_id:
        raise HTTPException(400, "external_id required")
    try:
        with db() as conn:
            row = conn.execute(
                "INSERT INTO records(external_id, district) VALUES (%s,%s) ON CONFLICT(external_id) DO UPDATE SET district=EXCLUDED.district RETURNING id, external_id, district, created_at",
                (external_id, district),
            ).fetchone()
        return {"id": row[0], "external_id": row[1], "district": row[2], "created_at": row[3]}
    except Exception as exc:
        DB_ERRORS.labels("create_record").inc()
        loki("error", "record insert failed", error=str(exc))
        raise HTTPException(503, detail=str(exc))


@app.post("/applications")
def create_application(payload: dict):
    try:
        with db() as conn:
            row = conn.execute(
                "INSERT INTO applications(record_id,status,payload) VALUES (%s,%s,%s) RETURNING id, created_at",
                (payload.get("record_id"), payload.get("status", "submitted"), json.dumps(payload.get("payload", {}))),
            ).fetchone()
        return {"id": row[0], "created_at": row[1]}
    except Exception as exc:
        DB_ERRORS.labels("create_application").inc()
        raise HTTPException(503, detail=str(exc))


@app.get("/applications/{application_id}")
def get_application(application_id: int):
    try:
        with db() as conn:
            row = conn.execute("SELECT id,record_id,status,payload,created_at FROM applications WHERE id=%s", (application_id,)).fetchone()
        if not row:
            raise HTTPException(404, "not found")
        return {"id": row[0], "record_id": row[1], "status": row[2], "payload": row[3], "created_at": row[4]}
    except HTTPException:
        raise
    except Exception as exc:
        DB_ERRORS.labels("get_application").inc()
        raise HTTPException(503, detail=str(exc))


@app.post("/rpo/probe/{sequence}")
def rpo_probe(sequence: int):
    try:
        with db() as conn:
            conn.execute("INSERT INTO rpo_probe(sequence) VALUES (%s) ON CONFLICT DO NOTHING", (sequence,))
        return {"acknowledged": sequence}
    except Exception as exc:
        DB_ERRORS.labels("rpo_probe").inc()
        raise HTTPException(503, detail=str(exc))


@app.get("/rpo/max")
def rpo_max():
    try:
        with db() as conn:
            row = conn.execute("SELECT COALESCE(max(sequence),0), count(*) FROM rpo_probe").fetchone()
        return {"max_sequence": row[0], "count": row[1]}
    except Exception as exc:
        DB_ERRORS.labels("rpo_max").inc()
        raise HTTPException(503, detail=str(exc))
