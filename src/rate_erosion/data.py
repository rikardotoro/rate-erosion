import re
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from rate_erosion.errors import InsufficientDataError, InvalidDataError, MissingColumnError

CANONICAL: dict[str, bool] = {
    "shipment": True,
    "date": True,
    "lane": True,
    "charge_code": True,
    "amount": True,
    "currency": False,
    "fx_rate": False,
}

ALIASES: dict[str, tuple[str, ...]] = {
    "shipment": ("shipment", "shipmentref", "shipmentreference", "reference",
                 "ref", "container", "bl", "blnumber", "hbl", "invoice"),
    "date": ("date", "invoicedate", "shipmentdate", "chargedate", "postingdate"),
    "lane": ("lane", "tradelane", "route", "corridor", "od", "origindestination"),
    "charge_code": ("chargecode", "charge", "chargetype", "costcode",
                    "category", "chargecategory", "code"),
    "amount": ("amount", "value", "cost", "chargeamount", "amt", "price"),
    "currency": ("currency", "ccy", "cur", "currencycode"),
    "fx_rate": ("fxrate", "fx", "exchangerate", "conversionrate"),
}

BASE_CODES: frozenset[str] = frozenset(
    {"bas", "base", "basefreight", "baserate", "oceanfreight", "ofr", "frt", "freight"}
)

CONTRACT_ALIASES: dict[str, tuple[str, ...]] = {
    "lane": ALIASES["lane"],
    "base_rate": ("baserate", "rate", "contractrate", "contractedrate", "basrate"),
}


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def is_base(code: str) -> bool:
    return _norm(code) in BASE_CODES


def _detect(columns: Sequence[str], spec: dict[str, bool],
            aliases: dict[str, tuple[str, ...]],
            overrides: dict[str, str] | None = None) -> dict[str, str]:
    overrides = overrides or {}
    lookup = {_norm(c): c for c in columns}
    mapping: dict[str, str] = {}

    for canonical, required in spec.items():
        if canonical in overrides:
            source = overrides[canonical]
            if source not in columns:
                raise MissingColumnError(
                    f"--map {canonical}={source}: column {source!r} is not in the file"
                )
            mapping[canonical] = source
            continue

        for alias in aliases[canonical]:
            if alias in lookup:
                mapping[canonical] = lookup[alias]
                break
        else:
            if required:
                raise MissingColumnError(
                    f"required column {canonical!r} not found; "
                    f"tried {', '.join(aliases[canonical])}. "
                    f"Use --map {canonical}=<your column> to set it explicitly."
                )
    return mapping


def detect_columns(
    columns: Sequence[str], overrides: dict[str, str] | None = None
) -> dict[str, str]:
    return _detect(columns, CANONICAL, ALIASES, overrides)


def load_cost_lines(
    path: Path, overrides: dict[str, str] | None = None
) -> pd.DataFrame:
    raw = pd.read_csv(path)
    mapping = detect_columns(list(raw.columns), overrides)
    frame = raw[list(mapping.values())].copy()
    frame.columns = list(mapping.keys())

    parsed = pd.to_datetime(frame["date"], errors="coerce")
    broke = frame["date"].notna() & parsed.isna()
    if broke.any():
        row = int(broke.idxmax())
        raise InvalidDataError(
            f"row {row}: could not parse date value {frame.loc[row, 'date']!r}"
        )
    frame["date"] = parsed

    amounts = pd.to_numeric(frame["amount"], errors="coerce")
    broke = frame["amount"].notna() & amounts.isna()
    if broke.any():
        row = int(broke.idxmax())
        raise InvalidDataError(
            f"row {row}: could not parse amount value {frame.loc[row, 'amount']!r}"
        )
    frame["amount"] = amounts.astype(float)

    if "currency" not in frame.columns:
        frame["currency"] = "USD"
    frame["currency"] = frame["currency"].fillna("USD").str.upper()

    if "fx_rate" not in frame.columns:
        frame["fx_rate"] = 1.0
    frame["fx_rate"] = pd.to_numeric(frame["fx_rate"], errors="coerce").fillna(1.0)

    ordered = [c for c in CANONICAL if c in frame.columns]
    return frame[ordered]


def load_contract(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    mapping = _detect(list(raw.columns), {"lane": True, "base_rate": True},
                      CONTRACT_ALIASES)
    contract = raw[list(mapping.values())].copy()
    contract.columns = list(mapping.keys())
    contract["base_rate"] = pd.to_numeric(contract["base_rate"], errors="coerce")

    bad = contract["base_rate"].isna() | (contract["base_rate"] <= 0)
    if bad.any():
        row = int(bad.idxmax())
        raise InvalidDataError(f"row {row}: base_rate must be a positive number")
    return contract.reset_index(drop=True)


def parse_period(text: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    match = re.fullmatch(r"(\d{4}-\d{2}):(\d{4}-\d{2})", text.strip())
    if not match:
        raise InvalidDataError(
            f"period {text!r} is not in YYYY-MM:YYYY-MM format, e.g. 2024-01:2024-06"
        )
    start = pd.Timestamp(match.group(1) + "-01")
    end = pd.Timestamp(match.group(2) + "-01") + pd.offsets.MonthEnd(0)
    if end < start:
        raise InvalidDataError(f"period {text!r} ends before it starts")
    return start, end


def _slice(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    start, end = parse_period(label)
    picked = frame[(frame["date"] >= start) & (frame["date"] <= end)]
    if picked.empty:
        raise InsufficientDataError(f"no cost lines fall inside {label}")
    return picked.reset_index(drop=True)


def split_periods(
    frame: pd.DataFrame,
    baseline: str | None = None,
    current: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    months = frame["date"].dt.to_period("M").sort_values().unique()
    if baseline is None:
        first = months[: min(3, len(months))]
        baseline = f"{first[0]}:{first[-1]}"
    if current is None:
        last = months[-min(3, len(months)):]
        current = f"{last[0]}:{last[-1]}"
    return _slice(frame, baseline), _slice(frame, current), baseline, current
