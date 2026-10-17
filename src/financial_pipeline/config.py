"""Configuração centralizada das séries SGS e do ambiente."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Series:
    code: int
    name: str
    frequency: str
    unit: str


SERIES = (
    Series(1178, "SELIC_ANNUAL", "daily", "percent_per_year"),
    Series(433, "IPCA_MONTHLY", "monthly", "percent_per_month"),
    Series(1, "USD_BRL_SELL", "daily", "BRL_per_USD"),
)


def database_url() -> str:
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("Defina DATABASE_URL (veja .env.example).")
    return value
