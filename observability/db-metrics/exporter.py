import os
import time
import httpx
import psycopg
from prometheus_client import Gauge, Counter, start_http_server

NODES = {
    "postgres1": (os.getenv("PG1_DSN"), os.getenv("PATRONI1_URL")),
    "postgres2": (os.getenv("PG2_DSN"), os.getenv("PATRONI2_URL")),
}
PRIMARY = Gauge("db_node_primary", "1 if Patroni reports node as leader", ["node"])
UP = Gauge("db_node_up", "1 if node can be queried", ["node"])
CONNS = Gauge("db_connections", "Current PostgreSQL connections", ["node"])
XACT = Gauge("db_xact_commit_total", "Committed transactions from pg_stat_database", ["node"])
LAG = Gauge("db_replication_lag_seconds", "Replica replay lag in seconds", ["node"])
SCRAPE_ERRORS = Counter("db_metrics_scrape_errors_total", "Exporter scrape failures", ["node"])


def collect_node(node, dsn, patroni):
    try:
        role = httpx.get(patroni, timeout=1).json().get("role", "")
        PRIMARY.labels(node).set(1 if role in ("master", "primary") else 0)
    except Exception:
        PRIMARY.labels(node).set(0)
    try:
        with psycopg.connect(dsn, connect_timeout=2, autocommit=True) as conn:
            conns = conn.execute("SELECT count(*) FROM pg_stat_activity").fetchone()[0]
            xact = conn.execute("SELECT COALESCE(sum(xact_commit),0) FROM pg_stat_database").fetchone()[0]
            lag = conn.execute("SELECT CASE WHEN pg_is_in_recovery() THEN COALESCE(EXTRACT(EPOCH FROM now()-pg_last_xact_replay_timestamp()),0) ELSE 0 END").fetchone()[0]
        UP.labels(node).set(1)
        CONNS.labels(node).set(conns)
        XACT.labels(node).set(xact)
        LAG.labels(node).set(float(lag or 0))
    except Exception:
        UP.labels(node).set(0)
        SCRAPE_ERRORS.labels(node).inc()


if __name__ == "__main__":
    start_http_server(9105)
    while True:
        for name, (dsn, patroni) in NODES.items():
            collect_node(name, dsn, patroni)
        time.sleep(2)
