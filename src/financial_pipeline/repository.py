"""Persistência idempotente no PostgreSQL usando UPSERT."""
from datetime import date, timedelta
from uuid import uuid4

import psycopg

from .config import Series


def latest_date(conn: psycopg.Connection, code: int) -> date | None:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(observed_on) FROM finance.observations WHERE series_code = %s", (code,))
        return cur.fetchone()[0]


def start_date_for(conn: psycopg.Connection, series: Series, initial: date, lookback_days: int) -> date:
    latest = latest_date(conn, series.code)
    return max(initial, latest - timedelta(days=lookback_days)) if latest else initial


def upsert_observations(conn: psycopg.Connection, rows: list[tuple]) -> int:
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO finance.observations (series_code, observed_on, value)
               VALUES (%s, %s, %s)
               ON CONFLICT (series_code, observed_on) DO UPDATE
               SET value = EXCLUDED.value, fetched_at = now()""",
            rows,
        )
    return len(rows)


def run_record(conn: psycopg.Connection, code: int, status: str, count: int, detail: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO finance.pipeline_runs (run_id, series_code, status, records_processed, detail)
               VALUES (%s, %s, %s, %s, %s)""",
            (uuid4(), code, status, count, detail),
        )
