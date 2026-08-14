import re
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd

from rate_erosion.errors import InsufficientDataError, UnknownSeriesError

SERIES: dict[str, str] = {
    "PCU483111483111": "PPI: Deep Sea Freight Transportation (BLS)",
    "PCU4883204883208": "PPI: Marine Cargo Handling — Containers (BLS)",
    "FRGEXPUSM649NCIS": "Cass Freight Index: Expenditures",
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


# currency -> (FRED series id, invert). The Fed's H.10 release quotes EUR, GBP,
# AUD and NZD as USD per unit; every other currency as units per USD (invert).
FX_SERIES: dict[str, tuple[str, bool]] = {
    "EUR": ("DEXUSEU", False),
    "GBP": ("DEXUSUK", False),
    "AUD": ("DEXUSAL", False),
    "NZD": ("DEXUSNZ", False),
    "JPY": ("DEXJPUS", True),
    "CNY": ("DEXCHUS", True),
    "CAD": ("DEXCAUS", True),
    "CHF": ("DEXSZUS", True),
    "MXN": ("DEXMXUS", True),
    "SEK": ("DEXSDUS", True),
    "NOK": ("DEXNOUS", True),
    "DKK": ("DEXDNUS", True),
    "INR": ("DEXINUS", True),
    "KRW": ("DEXKOUS", True),
    "SGD": ("DEXSIUS", True),
}


def fx_series_for(currency: str) -> tuple[str, bool]:
    try:
        return FX_SERIES[currency.upper()]
    except KeyError:
        raise UnknownSeriesError(
            f"no FRED exchange-rate series is registered for {currency!r}. "
            "Supply an fx_rate column for those lines, or use one of: "
            + ", ".join(sorted(FX_SERIES))
        ) from None


def fill_fx(
    frame: pd.DataFrame, cache_dir: Path, offline_dir: Path | None = None
) -> pd.DataFrame:
    """Fill missing fx_rate values from the Fed's daily rates, by line date.

    USD lines get 1.0; other currencies are looked up as-of the line date
    (backward, so weekends and holidays take the last published rate).
    Lines that already carry an fx_rate are never touched.
    """
    frame = frame.copy()
    missing = frame["fx_rate"].isna()
    frame.loc[missing & frame["currency"].eq("USD"), "fx_rate"] = 1.0

    for currency in sorted(frame.loc[frame["fx_rate"].isna(), "currency"].unique()):
        sid, invert = fx_series_for(currency)
        offline = (offline_dir / f"fred_{sid}.csv") if offline_dir else None
        if offline is not None and offline.exists():
            series = load_series(offline)
        else:
            series = fetch_series(sid, cache_dir)
        if invert:
            series = 1.0 / series

        rows = frame.index[frame["fx_rate"].isna() & frame["currency"].eq(currency)]
        rates = pd.merge_asof(
            frame.loc[rows, ["date"]].reset_index().sort_values("date"),
            series.rename("fx").rename_axis("date").reset_index().sort_values("date"),
            on="date", direction="backward",
        ).set_index("index")["fx"]
        frame.loc[rates.index, "fx_rate"] = rates

    still = frame["fx_rate"].isna()
    if still.any():
        row = int(still.idxmax())
        raise InsufficientDataError(
            f"row {row}: no exchange rate available on or before "
            f"{frame.loc[row, 'date'].date()} for {frame.loc[row, 'currency']}"
        )
    return frame


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
