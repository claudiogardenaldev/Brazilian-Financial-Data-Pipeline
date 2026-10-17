"""Entrypoint de linha de comando para ingestão incremental."""
import argparse
from datetime import date, datetime, timezone
from pathlib import Path
import json
import logging
import os

import psycopg
from dotenv import load_dotenv

from .client import fetch_series, normalize, make_session
from .config import SERIES, database_url
from .repository import start_date_for, upsert_observations, run_record

log = logging.getLogger(__name__)


def save_raw(folder: Path, code: int, payload: list[dict]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = folder / f"sgs_{code}_{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run(start: date, end: date, lookback: int, raw_dir: Path, codes: set[int] | None = None) -> None:
    if end < start or lookback < 0:
        raise ValueError("Período ou lookback inválido.")
    session = make_session()
    with psycopg.connect(database_url()) as conn:
        for series in SERIES:
            if codes is not None and series.code not in codes:
                continue
            left = start_date_for(conn, series, start, lookback)
            if left > end:
                log.info("%s: nada a atualizar; última data ultrapassa a data final", series.name)
                continue
            try:
                payload = fetch_series(series.code, left, end, session=session)
                raw_path = save_raw(raw_dir, series.code, payload)
                rows = normalize(series.code, payload, end=end)
                count = upsert_observations(conn, rows)
                run_record(conn, series.code, "success", count, str(raw_path))
                conn.commit()
                log.info("%s: %s registros processados, bruto em %s", series.name, count, raw_path)
            except Exception as exc:
                conn.rollback()
                # Grava o erro sem disfarçar a falha da execução.
                run_record(conn, series.code, "failed", 0, str(exc)[:1000])
                conn.commit()
                raise


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Pipeline de indicadores financeiros BCB/SGS")
    parser.add_argument("--start-date", default=os.getenv("START_DATE", "2024-01-01"), help="YYYY-MM-DD")
    parser.add_argument("--end-date", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--lookback-days", type=int, default=45)
    parser.add_argument("--raw-dir", default=os.getenv("RAW_DIR", "data/raw"))
    parser.add_argument("--series", nargs="*", type=int, help="Códigos SGS. Padrão: todas.")
    args = parser.parse_args()
    run(
        start=date.fromisoformat(args.start_date),
        end=date.fromisoformat(args.end_date),
        lookback=args.lookback_days,
        raw_dir=Path(args.raw_dir),
        codes=set(args.series) if args.series else None,
    )


if __name__ == "__main__":
    main()
