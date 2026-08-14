"""Pattern detectors over the cost-line history.

Two questions the decomposition tables cannot answer:
- WHEN did the rate actually move (regimes / changepoints)?
- Is money being relabelled between charge codes while the total stays
  flat (the surcharge shuffle — the classic way around a rate cap)?

Everything here is plain statistics on monthly per-shipment figures; no
fitted models, nothing that pretends to forecast.
"""
import numpy as np
import pandas as pd

from rate_erosion.data import is_base
from rate_erosion.decompose import converted


def monthly_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Rows: months. Columns: charge categories. Values: cost per shipment."""
    category = frame["charge_code"].map(
        lambda code: "base" if is_base(code) else str(code).upper()
    )
    month = frame["date"].dt.to_period("M")
    totals = converted(frame).groupby([month, category]).sum().unstack(fill_value=0.0)
    ships = frame.groupby(month)["shipment"].nunique()
    return totals.div(ships, axis=0)


def detect_shuffle(
    frame: pd.DataFrame,
    min_months: int = 8,
    ratio_threshold: float = 0.35,
    corr_threshold: float = -0.6,
    material_share: float = 0.015,
) -> dict | None:
    """The worst offsetting pair of charge categories, if one qualifies.

    A shuffle shows up as two components whose month-over-month moves cancel:
    their delta correlation is strongly negative and the variance of their sum
    is far below the sum of their variances.
    """
    matrix = monthly_matrix(frame)
    if len(matrix) < min_months:
        return None

    total = matrix.sum(axis=1).mean()
    material = [c for c in matrix.columns if matrix[c].mean() >= material_share * total]
    deltas = matrix[material].diff().dropna()

    best: dict | None = None
    for i, a in enumerate(material):
        for b in material[i + 1:]:
            da, db = deltas[a], deltas[b]
            var_a, var_b = float(da.var()), float(db.var())
            if var_a == 0.0 or var_b == 0.0:
                continue
            correlation = float(da.corr(db))
            offset_ratio = float((da + db).var()) / (var_a + var_b)
            if correlation < corr_threshold and offset_ratio < ratio_threshold:
                if best is None or correlation < best["correlation"]:
                    best = {"pair": (a, b), "correlation": correlation,
                            "offset_ratio": offset_ratio}
    return best


def _sse(x: np.ndarray) -> float:
    return float(((x - x.mean()) ** 2).sum()) if x.size else 0.0


def changepoints(
    series: pd.Series, min_size: int = 3, penalty: float | None = None
) -> list[int]:
    """Binary segmentation: indices where a new regime starts."""
    x = series.to_numpy(dtype=float)
    n = x.size
    if n < 2 * min_size:
        return []
    if penalty is None:
        diffs = np.diff(x)
        # median(diff^2) = 0.455 * 2 * sigma^2 for Gaussian noise; the 0.91
        # divisor removes that bias while staying robust to genuine steps
        noise = float(np.median(diffs**2)) / 0.91 if diffs.size else 0.0
        penalty = max(3.0 * noise * np.log(n), 1e-9)

    found: list[int] = []

    def split(lo: int, hi: int) -> None:
        if hi - lo < 2 * min_size:
            return
        base_cost = _sse(x[lo:hi])
        best_gain, best_k = 0.0, None
        for k in range(lo + min_size, hi - min_size + 1):
            gain = base_cost - _sse(x[lo:k]) - _sse(x[k:hi])
            if gain > best_gain:
                best_gain, best_k = gain, k
        if best_k is not None and best_gain > penalty:
            found.append(best_k)
            split(lo, best_k)
            split(best_k, hi)

    split(0, n)
    return sorted(found)


def rate_regimes(frame: pd.DataFrame, min_size: int = 3) -> list[dict]:
    """Steps in the all-in cost per shipment, with dates and magnitudes."""
    totals = monthly_matrix(frame).sum(axis=1)
    marks = changepoints(totals, min_size=min_size)
    bounds = [0, *marks, len(totals)]
    regimes = []
    for index, mark in enumerate(marks):
        before = float(totals.iloc[bounds[index]:mark].mean())
        after = float(totals.iloc[mark:bounds[index + 2]].mean())
        regimes.append({
            "month": str(totals.index[mark]),
            "before": before,
            "after": after,
            "step_pct": after / before - 1.0,
        })
    return regimes
