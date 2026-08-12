import pandas as pd

from rate_erosion.data import is_base
from rate_erosion.errors import InvalidDataError


def converted(frame: pd.DataFrame) -> pd.Series:
    return frame["amount"] * frame["fx_rate"]


def shipment_count(frame: pd.DataFrame) -> int:
    return int(frame["shipment"].nunique())


def per_shipment_by_category(frame: pd.DataFrame) -> dict[str, float]:
    n = shipment_count(frame)
    category = frame["charge_code"].map(
        lambda code: "base" if is_base(code) else str(code).upper()
    )
    totals = converted(frame).groupby(category).sum()
    return {cat: float(total) / n for cat, total in totals.items()}


def waterfall(
    current: pd.DataFrame, contract: pd.DataFrame
) -> list[tuple[str, float]]:
    n = shipment_count(current)
    lane_counts = current.groupby("lane")["shipment"].nunique()
    rates = contract.set_index("lane")["base_rate"]

    missing = sorted(set(lane_counts.index) - set(rates.index))
    if missing:
        raise InvalidDataError(
            f"lanes not in the contract: {', '.join(missing)}. "
            "Add them to the contract CSV or filter them out."
        )

    contracted = float((lane_counts * rates).dropna().sum()) / n
    categories = per_shipment_by_category(current)
    base_paid = categories.pop("base", 0.0)

    steps: list[tuple[str, float]] = [
        ("Contracted base", contracted),
        ("Base rate creep", base_paid - contracted),
    ]
    steps += sorted(categories.items(), key=lambda item: -item[1])
    steps.append(("Realised all-in", base_paid + sum(categories.values())))
    return steps


def _neutral_fx(base: pd.DataFrame) -> dict[str, float]:
    return base.groupby("currency")["fx_rate"].mean().to_dict()


def _neutral_value(frame: pd.DataFrame, fx_map: dict[str, float]) -> pd.Series:
    rates = frame["currency"].map(fx_map).fillna(frame["fx_rate"])
    return frame["amount"] * rates


def variance(base: pd.DataFrame, cur: pd.DataFrame) -> dict[str, float]:
    fx_map = _neutral_fx(base)

    def lane_stats(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        value = _neutral_value(frame, fx_map).groupby(frame["lane"]).sum()
        ships = frame.groupby("lane")["shipment"].nunique().astype(float)
        return value / ships, ships

    c_base, n_base = lane_stats(base)
    c_cur, n_cur = lane_stats(cur)

    total_base_n = float((c_base * n_base).sum())
    total_cur_n = float((c_cur * n_cur).sum())
    total_base_a = float(converted(base).sum())
    total_cur_a = float(converted(cur).sum())

    big_n_base, big_n_cur = float(n_base.sum()), float(n_cur.sum())
    k = big_n_cur / big_n_base
    avg_base = total_base_n / big_n_base

    reference = c_base.reindex(c_cur.index).fillna(avg_base)
    n_base_aligned = n_base.reindex(c_cur.index).fillna(0.0)

    volume = (k - 1.0) * total_base_n
    price = float((n_cur * (c_cur - reference)).sum())
    mix = float(((n_cur - k * n_base_aligned) * reference).sum())
    fx = (total_cur_a - total_cur_n) - (total_base_a - total_base_n)

    return {
        "total_change": total_cur_a - total_base_a,
        "volume": volume,
        "price": price,
        "mix": mix,
        "fx": fx,
    }
