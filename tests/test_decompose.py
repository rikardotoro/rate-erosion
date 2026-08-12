import numpy as np
import pandas as pd
import pytest

from rate_erosion.decompose import variance


def _lines(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame.get("date", "2024-01-15"))
    frame["charge_code"] = frame.get("charge_code", "BAS")
    frame["currency"] = frame.get("currency", "USD")
    if "fx_rate" not in frame.columns:
        frame["fx_rate"] = 1.0
    return frame


def test_effects_sum_exactly_to_total_change():
    rng = np.random.default_rng(5)

    def period(tag, n):
        rows = []
        for i in range(n):
            lane = rng.choice(["A", "B", "C"])
            ccy, fx = (("EUR", rng.uniform(1.0, 1.2)) if lane == "B" else ("USD", 1.0))
            rows.append({"shipment": f"{tag}{i}", "lane": lane,
                         "amount": rng.uniform(900, 2600),
                         "currency": ccy, "fx_rate": fx})
        return _lines(rows)

    base, cur = period("b", 80), period("c", 120)
    result = variance(base, cur)
    parts = result["volume"] + result["price"] + result["mix"] + result["fx"]
    assert parts == pytest.approx(result["total_change"], abs=1e-6)


def test_mix_shift_is_not_booked_as_price():
    """Trap 2: same per-lane prices, mix moves to the dear lane — price effect is zero."""
    base = _lines(
        [{"shipment": f"b{i}", "lane": "CHEAP", "amount": 1000} for i in range(8)]
        + [{"shipment": f"B{i}", "lane": "DEAR", "amount": 3000} for i in range(2)]
    )
    cur = _lines(
        [{"shipment": f"c{i}", "lane": "CHEAP", "amount": 1000} for i in range(2)]
        + [{"shipment": f"C{i}", "lane": "DEAR", "amount": 3000} for i in range(8)]
    )
    result = variance(base, cur)
    assert result["price"] == pytest.approx(0.0, abs=1e-9)
    assert result["volume"] == pytest.approx(0.0, abs=1e-9)
    assert result["mix"] > 0


def test_fx_movement_is_not_a_rate_change():
    """Trap 3: same EUR amounts, only the exchange rate moved — price effect is zero."""
    base = _lines([{"shipment": f"b{i}", "lane": "A", "amount": 1000,
                    "currency": "EUR", "fx_rate": 1.05} for i in range(5)])
    cur = _lines([{"shipment": f"c{i}", "lane": "A", "amount": 1000,
                   "currency": "EUR", "fx_rate": 1.15} for i in range(5)])
    result = variance(base, cur)
    assert result["price"] == pytest.approx(0.0, abs=1e-9)
    assert result["fx"] == pytest.approx(5 * 1000 * 0.10, abs=1e-9)


def test_pure_volume_change():
    base = _lines([{"shipment": f"b{i}", "lane": "A", "amount": 1000} for i in range(5)])
    cur = _lines([{"shipment": f"c{i}", "lane": "A", "amount": 1000} for i in range(10)])
    result = variance(base, cur)
    assert result["volume"] == pytest.approx(5000.0)
    assert result["price"] == pytest.approx(0.0, abs=1e-9)
    assert result["mix"] == pytest.approx(0.0, abs=1e-9)


def test_new_lane_in_current_period_does_not_crash():
    base = _lines([{"shipment": "b0", "lane": "A", "amount": 1000}])
    cur = _lines([
        {"shipment": "c0", "lane": "A", "amount": 1000},
        {"shipment": "c1", "lane": "NEW", "amount": 2000},
    ])
    result = variance(base, cur)
    parts = result["volume"] + result["price"] + result["mix"] + result["fx"]
    assert parts == pytest.approx(result["total_change"], abs=1e-9)
