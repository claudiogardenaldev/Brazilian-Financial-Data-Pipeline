"""Cliente HTTP para a API SGS do Banco Central."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
# A API limita séries diárias a consultas com intervalos de até dez anos.
CHUNK_DAYS = 3650


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"Accept": "application/json", "User-Agent": "financial-pipeline-portfolio/1.0"})
    return session


def date_windows(start: date, end: date) -> Iterable[tuple[date, date]]:
    if end < start:
        return
    cursor = start
    while cursor <= end:
        last = min(cursor + timedelta(days=CHUNK_DAYS - 1), end)
        yield cursor, last
        cursor = last + timedelta(days=1)


def fetch_series(code: int, start: date, end: date, session: requests.Session | None = None) -> list[dict]:
    if start > end:
        raise ValueError("Data inicial posterior à final.")
    s = session or make_session()
    records: list[dict] = []
    for left, right in date_windows(start, end):
        response = s.get(
            BASE_URL.format(code=code),
            params={
                "formato": "json",
                "dataInicial": left.strftime("%d/%m/%Y"),
                "dataFinal": right.strftime("%d/%m/%Y"),
            },
            timeout=40,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError(f"SGS {code}: resposta JSON inesperada.")
        records.extend(payload)
    return records


def normalize(code: int, payload: list[dict], end: date) -> list[tuple[int, date, Decimal]]:
    """Validação estrita de registros antes da persistência."""
    from datetime import datetime

    found = set()
    rows: list[tuple[int, date, Decimal]] = []
    for item in payload:
        if not isinstance(item, dict) or "data" not in item or "valor" not in item:
            raise ValueError("Registro SGS sem data/valor.")
        try:
            observed = datetime.strptime(item["data"], "%d/%m/%Y").date()
            amount = Decimal(str(item["valor"]).replace(",", "."))
        except (ValueError, InvalidOperation, TypeError) as exc:
            raise ValueError(f"SGS {code}: registro inválido: {item!r}") from exc
        if not amount.is_finite() or observed > end or (code in (1178, 1) and amount <= 0):
            raise ValueError(f"SGS {code}: dado fora das regras de qualidade: {item!r}")
        if observed in found:
            raise ValueError(f"SGS {code}: data duplicada na resposta: {observed}")
        found.add(observed)
        rows.append((code, observed, amount))
    return sorted(rows, key=lambda row: row[1])
