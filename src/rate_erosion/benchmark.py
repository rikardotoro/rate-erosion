import re
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd

from rate_erosion.errors import InsufficientDataError, UnknownSeriesError

SERIES: dict[str, str] = {
    "PCU483111483111": "PPI: Deep Sea Freight Transportation (BLS)",
    "PCU4883204883208": "PPI: Marine Cargo Handling — Containers (BLS)",
    "FRGSHPUSM649NCIS": "Cass Freight Index: Shipments",
}

DEFAULT_SERIES = "PCU483111483111"

_BALTIC = {"bdi", "baltic", "balticdry", "balticdryindex"}

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def resolve_series(name: str) -> str:
    if _norm(name) in _BALTIC:
        raise UnknownSeriesError(
            "The Baltic Dry Index measures dry bulk (iron ore, grain, coal), "
            "not containers. It is the famous one, and it is the wrong one. "
            f"Supported series: {', '.join(SERIES)}."
        )
    for sid in SERIES:
        if _norm(name) == _norm(sid):
            return sid
    raise UnknownSeriesError(
        f"unknown series {name!r}. Supported: "
        + "; ".join(f"{sid} ({title})" for sid, title in SERIES.items())
    )


def load_series(source: Path) -> pd.Series:
    frame = pd.read_csv(source)
    date_col, value_col = frame.columns[0], frame.columns[1]
    values = pd.to_numeric(frame[value_col], errors="coerce")
    series = pd.Series(
        values.values, index=pd.to_datetime(frame[date_col]), name=value_col
    ).dropna()
    if series.empty:
        raise InsufficientDataError(f"{source} contains no usable observations")
    return series


def fetch_series(series_id: str, cache_dir: Path) -> pd.Series:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f"{series_id}.csv"
    try:
        with urlopen(FRED_URL.format(sid=series_id), timeout=30) as response:
            cache.write_bytes(response.read())
    except (URLError, OSError):
        if not cache.exists():
            raise InsufficientDataError(
                f"could not reach FRED and no cached copy of {series_id} exists. "
                "Run once with network access, or pass --benchmark none."
            ) from None
    return load_series(cache)


def pct_change(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> float:
    picked = series.sort_index()
    first = picked.asof(start) if picked.index[0] <= start else picked.iloc[0]
    last = picked.asof(end)
    if pd.isna(first) or pd.isna(last):
        raise InsufficientDataError("benchmark series does not cover the period")
    return float(last) / float(first) - 1.0


def verdict(yours_pct: float, market_pct: float) -> dict[str, float]:
    return {
        "yours": yours_pct,
        "market": market_pct,
        "outperformance": market_pct - yours_pct,
    }
