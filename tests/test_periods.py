import pandas as pd
import pytest

from rate_erosion.data import parse_period, split_periods
from rate_erosion.errors import InsufficientDataError, InvalidDataError


def _frame(dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame({
        "shipment": [f"S{i}" for i in range(len(dates))],
        "date": pd.to_datetime(dates),
        "lane": "L",
        "charge_code": "BAS",
        "amount": 100.0,
        "currency": "USD",
        "fx_rate": 1.0,
    })


def test_parse_period_is_month_inclusive():
    start, end = parse_period("2024-01:2024-03")
    assert start == pd.Timestamp("2024-01-01")
    assert end == pd.Timestamp("2024-03-31")


def test_parse_period_rejects_garbage():
    with pytest.raises(InvalidDataError, match="YYYY-MM:YYYY-MM"):
        parse_period("january to march")


def test_explicit_periods_select_rows():
    frame = _frame(["2024-01-15", "2024-02-15", "2025-05-15", "2025-06-15"])
    base, cur, base_label, cur_label = split_periods(
        frame, baseline="2024-01:2024-02", current="2025-05:2025-06"
    )
    assert len(base) == 2 and len(cur) == 2
    assert base_label == "2024-01:2024-02"


def test_default_periods_are_first_and_last_three_months():
    dates = [f"2024-{m:02d}-10" for m in range(1, 13)]
    base, cur, base_label, cur_label = split_periods(_frame(dates))
    assert base_label == "2024-01:2024-03"
    assert cur_label == "2024-10:2024-12"
    assert len(base) == 3 and len(cur) == 3


def test_empty_period_raises():
    frame = _frame(["2024-01-15", "2024-02-15"])
    with pytest.raises(InsufficientDataError, match="2030-01:2030-02"):
        split_periods(frame, baseline="2030-01:2030-02", current="2024-01:2024-02")
