from datetime import date
from unittest.mock import patch

from financial_pipeline.config import SERIES
from financial_pipeline.repository import start_date_for


def test_initial_load_uses_start_date():
    with patch("financial_pipeline.repository.latest_date", return_value=None):
        assert start_date_for(None, SERIES[0], date(2024, 1, 1), 45) == date(2024, 1, 1)


def test_incremental_load_revisits_lookback_window():
    with patch("financial_pipeline.repository.latest_date", return_value=date(2026, 10, 1)):
        assert start_date_for(None, SERIES[0], date(2024, 1, 1), 30) == date(2026, 9, 1)
