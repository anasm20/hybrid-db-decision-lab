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
            in_recovery = conn.execute("SELECT pg_is_in_recovery()").fetchone()[0]
            if in_recovery:
                # Lag for a standby is reported by the primary below (pg_stat_replication),
                # not measured here — see the note in the primary branch for why.
                pass
            else:
                LAG.labels(node).set(0.0)
                # pg_stat_replication.replay_lag is fed by WAL-receiver feedback and reflects
                # the *current* delay. A naive "now() - pg_last_xact_replay_timestamp()" on the
                # standby instead measures time since the last write was replayed, which grows
                # unbounded during idle periods even though the standby is fully caught up.
                rows = conn.execute(
                    "SELECT application_name, EXTRACT(EPOCH FROM replay_lag) FROM pg_stat_replication"
                ).fetchall()
                for app_name, lag_seconds in rows:
                    if app_name in NODES:
                        LAG.labels(app_name).set(float(lag_seconds or 0))
        UP.labels(node).set(1)
        CONNS.labels(node).set(conns)
        XACT.labels(node).set(xact)
    except Exception:
        UP.labels(node).set(0)
        SCRAPE_ERRORS.labels(node).inc()


if __name__ == "__main__":
    start_http_server(9105)
    while True:
        for name, (dsn, patroni) in NODES.items():
            collect_node(name, dsn, patroni)
        time.sleep(2)
