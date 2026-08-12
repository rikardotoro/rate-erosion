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
