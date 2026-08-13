from pathlib import Path

import pandas as pd
import pytest

from rate_erosion.benchmark import fill_fx, fx_series_for
from rate_erosion.errors import InsufficientDataError, UnknownSeriesError


def _frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"])
    frame["shipment"] = [f"S{i}" for i in range(len(rows))]
    frame["lane"] = "L"
    frame["charge_code"] = "THC"
    frame["amount"] = 100.0
    if "fx_rate" not in frame.columns:
        frame["fx_rate"] = float("nan")
    return frame


def _slice(tmp_path: Path, sid: str, rows: list[tuple[str, float]]) -> Path:
    path = tmp_path / f"fred_{sid}.csv"
    path.write_text("DATE," + sid + "\n"
                    + "\n".join(f"{d},{v}" for d, v in rows) + "\n")
    return path


def test_usd_lines_fill_with_one(tmp_path):
    frame = _frame([{"date": "2021-01-05", "currency": "USD"}])
    filled = fill_fx(frame, tmp_path, offline_dir=tmp_path)
    assert filled.loc[0, "fx_rate"] == 1.0


def test_eur_fills_asof_the_line_date(tmp_path):
    _slice(tmp_path, "DEXUSEU", [("2021-01-01", 1.22), ("2021-01-04", 1.23)])
    frame = _frame([
        {"date": "2021-01-03", "currency": "EUR"},   # Sunday -> Friday's rate
        {"date": "2021-01-04", "currency": "EUR"},
    ])
    filled = fill_fx(frame, tmp_path, offline_dir=tmp_path)
    assert filled.loc[0, "fx_rate"] == pytest.approx(1.22)
    assert filled.loc[1, "fx_rate"] == pytest.approx(1.23)


def test_units_per_usd_series_is_inverted(tmp_path):
    _slice(tmp_path, "DEXJPUS", [("2021-01-04", 104.0)])
    frame = _frame([{"date": "2021-01-05", "currency": "JPY"}])
    filled = fill_fx(frame, tmp_path, offline_dir=tmp_path)
    assert filled.loc[0, "fx_rate"] == pytest.approx(1 / 104.0)


def test_user_supplied_fx_is_never_touched(tmp_path):
    _slice(tmp_path, "DEXUSEU", [("2021-01-01", 1.22)])
    frame = _frame([{"date": "2021-01-05", "currency": "EUR", "fx_rate": 1.50}])
    filled = fill_fx(frame, tmp_path, offline_dir=tmp_path)
    assert filled.loc[0, "fx_rate"] == 1.50


def test_unknown_currency_says_how_to_fix_it():
    with pytest.raises(UnknownSeriesError, match="fx_rate"):
        fx_series_for("COP")


def test_date_before_series_start_raises(tmp_path):
    _slice(tmp_path, "DEXUSEU", [("2021-02-01", 1.21)])
    frame = _frame([{"date": "2021-01-15", "currency": "EUR"}])
    with pytest.raises(InsufficientDataError, match="row 0"):
        fill_fx(frame, tmp_path, offline_dir=tmp_path)
