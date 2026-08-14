import numpy as np
import pandas as pd
import pytest

from rate_erosion.patterns import changepoints, detect_shuffle, monthly_matrix, rate_regimes


def _lines(monthly_amounts: dict[str, list[float]], ships_per_month: int = 4) -> pd.DataFrame:
    """One frame from per-month per-shipment amounts per charge code."""
    n_months = len(next(iter(monthly_amounts.values())))
    rows = []
    for m in range(n_months):
        month = pd.Timestamp("2021-01-01") + pd.DateOffset(months=m)
        for s in range(ships_per_month):
            sid = f"{m:02d}-{s}"
            for code, amounts in monthly_amounts.items():
                if amounts[m] == 0.0:
                    continue
                rows.append({"shipment": sid, "date": month, "lane": "L",
                             "charge_code": code, "amount": float(amounts[m]),
                             "currency": "USD", "fx_rate": 1.0})
    return pd.DataFrame(rows)


def test_monthly_matrix_is_per_shipment():
    frame = _lines({"BAS": [1000.0] * 3, "BAF": [300.0] * 3})
    matrix = monthly_matrix(frame)
    assert matrix.loc[matrix.index[0], "base"] == pytest.approx(1000.0)
    assert matrix.loc[matrix.index[0], "BAF"] == pytest.approx(300.0)


def test_planted_shuffle_is_detected():
    """Trap 5: the all-in stays flat while money migrates between codes."""
    months = 14
    baf = [380.0] * 8 + [270.0] * (months - 8)
    lss = [0.0] * 8 + [110.0] * (months - 8)
    frame = _lines({"BAS": [2000.0] * months, "BAF": baf, "LSS": lss,
                    "DOC": [45.0] * months})
    result = detect_shuffle(frame)
    assert result is not None
    assert set(result["pair"]) == {"BAF", "LSS"}
    assert result["correlation"] < -0.6
    assert result["offset_ratio"] < 0.35


def test_independent_movement_is_not_a_shuffle():
    months = 14
    rng = np.random.default_rng(3)
    baf = (380 + rng.normal(0, 25, months).cumsum()).tolist()
    thc = [220.0 + 6.0 * m for m in range(months)]  # steady rise, unrelated
    frame = _lines({"BAS": [2000.0] * months, "BAF": baf, "THC": thc})
    assert detect_shuffle(frame) is None


def test_joint_increases_are_not_a_shuffle():
    months = 14
    up = [300.0 + 10.0 * m for m in range(months)]
    frame = _lines({"BAS": [2000.0] * months, "BAF": up, "THC": up})
    assert detect_shuffle(frame) is None


def test_too_few_months_returns_none():
    frame = _lines({"BAS": [2000.0] * 5, "BAF": [380.0] * 5})
    assert detect_shuffle(frame) is None


def test_changepoints_find_a_single_step():
    rng = np.random.default_rng(1)
    series = pd.Series(
        np.concatenate([100 + rng.normal(0, 2, 10), 130 + rng.normal(0, 2, 8)])
    )
    found = changepoints(series)
    assert found == [10]


def test_changepoints_ignore_pure_noise():
    rng = np.random.default_rng(2)
    series = pd.Series(100 + rng.normal(0, 2, 18))
    assert changepoints(series) == []


def test_changepoints_find_two_steps():
    rng = np.random.default_rng(4)
    series = pd.Series(np.concatenate([
        100 + rng.normal(0, 1.5, 8),
        140 + rng.normal(0, 1.5, 6),
        110 + rng.normal(0, 1.5, 6),
    ]))
    assert changepoints(series) == [8, 14]


def test_rate_regimes_report_step_direction():
    months = 16
    total = [2800.0] * 8 + [3050.0] * (months - 8)
    frame = _lines({"BAS": total})
    regimes = rate_regimes(frame)
    assert len(regimes) == 1
    assert regimes[0]["month"] == "2021-09"
    assert regimes[0]["step_pct"] == pytest.approx(250 / 2800, rel=0.05)
