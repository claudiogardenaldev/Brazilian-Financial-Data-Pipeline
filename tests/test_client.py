from datetime import date
from decimal import Decimal
import pytest

from financial_pipeline.client import date_windows, fetch_series, normalize


class FakeResponse:
    def raise_for_status(self):
        pass
    def json(self):
        return [{"data": "02/01/2024", "valor": "5.1234"}]


class FakeSession:
    def __init__(self):
        self.calls = []
    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        return FakeResponse()


def test_date_windows_cover_full_period_without_overlap():
    start, end = date(2014, 1, 1), date(2026, 1, 1)
    windows = list(date_windows(start, end))
    assert len(windows) == 2
    assert windows[0][0] == start and windows[-1][1] == end
    assert (windows[1][0] - windows[0][1]).days == 1
    assert all((right - left).days < 3650 for left, right in windows)


def test_fetch_series_builds_sgs_request():
    session = FakeSession()
    result = fetch_series(433, date(2024, 1, 1), date(2024, 1, 31), session)
    assert len(result) == 1
    assert session.calls[0][1]["formato"] == "json"
    assert session.calls[0][1]["dataInicial"] == "01/01/2024"


def test_normalize_parses_brazilian_number():
    rows = normalize(433, [{"data": "01/01/2024", "valor": "-0,08"}], date(2024, 2, 1))
    assert rows == [(433, date(2024, 1, 1), Decimal("-0.08"))]


def test_normalize_rejects_duplicate_and_future():
    row = {"data": "01/01/2024", "valor": "1.5"}
    with pytest.raises(ValueError, match="duplicada"):
        normalize(1178, [row, row], date(2024, 1, 31))
    with pytest.raises(ValueError, match="qualidade"):
        normalize(1, [{"data": "01/02/2024", "valor": "5"}], date(2024, 1, 31))


def test_negative_ipca_allowed_but_dollar_rejected():
    payload = [{"data": "01/01/2024", "valor": "-0.3"}]
    assert normalize(433, payload, date(2024, 1, 31))
    with pytest.raises(ValueError):
        normalize(1, payload, date(2024, 1, 31))
