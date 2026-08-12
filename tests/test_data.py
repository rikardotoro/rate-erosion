from pathlib import Path

import pandas as pd
import pytest

from rate_erosion.data import detect_columns, is_base, load_contract, load_cost_lines
from rate_erosion.errors import InvalidDataError, MissingColumnError


def _write(tmp_path: Path, rows: list[dict], name: str = "lines.csv") -> Path:
    path = tmp_path / name
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_detects_canonical_names():
    cols = ["shipment", "date", "lane", "charge_code", "amount"]
    assert detect_columns(cols)["shipment"] == "shipment"


def test_detects_common_aliases():
    cols = ["BL Number", "Invoice Date", "Trade Lane", "Charge Type", "Value", "CCY"]
    mapping = detect_columns(cols)
    assert mapping["shipment"] == "BL Number"
    assert mapping["date"] == "Invoice Date"
    assert mapping["lane"] == "Trade Lane"
    assert mapping["charge_code"] == "Charge Type"
    assert mapping["amount"] == "Value"
    assert mapping["currency"] == "CCY"


def test_override_beats_detection():
    cols = ["shipment", "date", "lane", "charge_code", "amount", "posted"]
    mapping = detect_columns(cols, overrides={"date": "posted"})
    assert mapping["date"] == "posted"


def test_missing_required_column_names_the_column():
    cols = ["shipment", "date", "lane", "amount"]
    with pytest.raises(MissingColumnError, match="charge_code"):
        detect_columns(cols)


def test_base_codes_are_recognised_case_insensitively():
    assert is_base("BAS")
    assert is_base("Ocean Freight")
    assert not is_base("BAF")


def test_load_defaults_currency_and_fx(tmp_path):
    path = _write(tmp_path, [
        {"shipment": "S1", "date": "2024-01-05", "lane": "CNSHA-USLAX",
         "charge_code": "BAS", "amount": 2000},
    ])
    frame = load_cost_lines(path)
    assert frame.loc[0, "currency"] == "USD"
    assert frame.loc[0, "fx_rate"] == 1.0
    assert frame.loc[0, "date"] == pd.Timestamp("2024-01-05")


def test_unparseable_date_names_the_row(tmp_path):
    path = _write(tmp_path, [
        {"shipment": "S1", "date": "not-a-date", "lane": "L",
         "charge_code": "BAS", "amount": 100},
    ])
    with pytest.raises(InvalidDataError, match="row 0"):
        load_cost_lines(path)


def test_non_numeric_amount_names_the_row(tmp_path):
    path = _write(tmp_path, [
        {"shipment": "S1", "date": "2024-01-05", "lane": "L",
         "charge_code": "BAS", "amount": "two thousand"},
    ])
    with pytest.raises(InvalidDataError, match="row 0"):
        load_cost_lines(path)


def test_load_contract(tmp_path):
    path = _write(tmp_path, [
        {"lane": "CNSHA-USLAX", "base_rate": 1950},
        {"lane": "CNSHA-NLRTM", "base_rate": 2450},
    ], name="contract.csv")
    contract = load_contract(path)
    assert list(contract.columns) == ["lane", "base_rate"]
    assert contract.loc[0, "base_rate"] == 1950.0


def test_contract_rejects_non_positive_rate(tmp_path):
    path = _write(tmp_path, [{"lane": "L", "base_rate": 0}], name="contract.csv")
    with pytest.raises(InvalidDataError, match="row 0"):
        load_contract(path)
