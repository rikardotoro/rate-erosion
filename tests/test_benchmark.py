import pandas as pd
import pytest

from rate_erosion.benchmark import (
    DEFAULT_SERIES,
    SERIES,
    load_series,
    pct_change,
    resolve_series,
    verdict,
)
from rate_erosion.errors import UnknownSeriesError


def test_default_series_is_registered():
    assert DEFAULT_SERIES in SERIES


def test_resolve_accepts_a_known_id():
    assert resolve_series("PCU483111483111") == "PCU483111483111"


def test_baltic_dry_index_is_refused_with_explanation():
    """Trap 1: the famous index measures dry bulk, not containers."""
    with pytest.raises(UnknownSeriesError, match="dry bulk"):
        resolve_series("BDI")
    with pytest.raises(UnknownSeriesError, match="dry bulk"):
        resolve_series("baltic dry index")


def test_unknown_series_lists_the_supported_ones():
    with pytest.raises(UnknownSeriesError, match="PCU483111483111"):
        resolve_series("SOMETHING")


def test_load_series_parses_fredgraph_csv(tmp_path):
    path = tmp_path / "fred.csv"
    path.write_text(
        "DATE,PCU483111483111\n"
        "2024-01-01,150.0\n2024-02-01,.\n2024-03-01,156.0\n"
    )
    series = load_series(path)
    assert len(series) == 2  # the '.' row is dropped
    assert series.loc[pd.Timestamp("2024-03-01")] == 156.0


def test_pct_change_uses_asof_values(tmp_path):
    path = tmp_path / "fred.csv"
    path.write_text(
        "DATE,X\n2024-01-01,100.0\n2024-06-01,110.0\n2024-12-01,130.0\n"
    )
    series = load_series(path)
    change = pct_change(series, pd.Timestamp("2024-01-15"), pd.Timestamp("2024-12-15"))
    assert change == pytest.approx(0.30)


def test_verdict_reports_relative_points():
    """Trap 4: a rate change means nothing until it is compared to the market."""
    result = verdict(yours_pct=0.12, market_pct=0.30)
    assert result["outperformance"] == pytest.approx(0.18)
