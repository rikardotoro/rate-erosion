import pandas as pd
import pytest

from rate_erosion.decompose import per_shipment_by_category, shipment_count, waterfall
from rate_erosion.errors import InvalidDataError


def _lines(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame.get("date", "2024-01-15"))
    frame["currency"] = frame.get("currency", "USD")
    frame["fx_rate"] = frame.get("fx_rate", 1.0)
    return frame


CONTRACT = pd.DataFrame({"lane": ["A", "B"], "base_rate": [1000.0, 2000.0]})


def test_shipment_count_is_distinct_references():
    frame = _lines([
        {"shipment": "S1", "lane": "A", "charge_code": "BAS", "amount": 1000},
        {"shipment": "S1", "lane": "A", "charge_code": "BAF", "amount": 200},
        {"shipment": "S2", "lane": "A", "charge_code": "BAS", "amount": 1000},
    ])
    assert shipment_count(frame) == 2


def test_base_codes_fold_into_base_category():
    frame = _lines([
        {"shipment": "S1", "lane": "A", "charge_code": "Ocean Freight", "amount": 1000},
        {"shipment": "S1", "lane": "A", "charge_code": "BAF", "amount": 200},
    ])
    cats = per_shipment_by_category(frame)
    assert cats["base"] == 1000.0
    assert cats["BAF"] == 200.0


def test_waterfall_steps_sum_to_realised():
    frame = _lines([
        {"shipment": "S1", "lane": "A", "charge_code": "BAS", "amount": 1050},
        {"shipment": "S1", "lane": "A", "charge_code": "BAF", "amount": 300},
        {"shipment": "S1", "lane": "A", "charge_code": "THC", "amount": 150},
        {"shipment": "S2", "lane": "B", "charge_code": "BAS", "amount": 2100},
        {"shipment": "S2", "lane": "B", "charge_code": "BAF", "amount": 300},
    ])
    steps = waterfall(frame, CONTRACT)
    labels = [s[0] for s in steps]
    assert labels[0] == "Contracted base"
    assert labels[1] == "Base rate creep"
    assert labels[-1] == "Realised all-in"
    # contracted = (1*1000 + 1*2000) / 2 = 1500; base paid = (1050+2100)/2 = 1575
    assert steps[0][1] == pytest.approx(1500.0)
    assert dict(steps)["Base rate creep"] == pytest.approx(75.0)
    middle = sum(v for _, v in steps[1:-1])
    assert steps[0][1] + middle == pytest.approx(steps[-1][1])


def test_surcharges_sorted_by_impact():
    frame = _lines([
        {"shipment": "S1", "lane": "A", "charge_code": "BAS", "amount": 1000},
        {"shipment": "S1", "lane": "A", "charge_code": "DOC", "amount": 45},
        {"shipment": "S1", "lane": "A", "charge_code": "BAF", "amount": 400},
    ])
    steps = waterfall(frame, CONTRACT)
    surcharge_labels = [s[0] for s in steps[2:-1]]
    assert surcharge_labels == ["BAF", "DOC"]


def test_lane_missing_from_contract_is_an_error():
    frame = _lines([
        {"shipment": "S1", "lane": "UNKNOWN", "charge_code": "BAS", "amount": 1000},
    ])
    with pytest.raises(InvalidDataError, match="UNKNOWN"):
        waterfall(frame, CONTRACT)
