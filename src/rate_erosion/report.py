from dataclasses import asdict, dataclass

import pandas as pd
from rich.console import Console
from rich.table import Table

from rate_erosion.benchmark import pct_change, verdict
from rate_erosion.data import parse_period, split_periods
from rate_erosion.decompose import converted, shipment_count, variance, waterfall
from rate_erosion.patterns import detect_shuffle, rate_regimes


@dataclass
class Analysis:
    baseline: str
    current: str
    n_base: int
    n_cur: int
    contracted: float
    realised: float
    waterfall: list[tuple[str, float]]
    effects: dict[str, float]
    yours_pct: float
    benchmark: dict | None
    regimes: list[dict]
    shuffle: dict | None


def analyse(
    lines: pd.DataFrame,
    contract: pd.DataFrame,
    baseline: str | None,
    current: str | None,
    market: pd.Series | None,
    market_title: str | None,
) -> Analysis:
    base, cur, base_label, cur_label = split_periods(lines, baseline, current)

    avg_base = float(converted(base).sum()) / shipment_count(base)
    avg_cur = float(converted(cur).sum()) / shipment_count(cur)
    yours_pct = avg_cur / avg_base - 1.0

    steps = waterfall(cur, contract)

    bench = None
    if market is not None:
        start, _ = parse_period(base_label)
        _, end = parse_period(cur_label)
        market_pct = pct_change(market, start, end)
        bench = {"title": market_title, **verdict(yours_pct, market_pct)}

    return Analysis(
        baseline=base_label,
        current=cur_label,
        n_base=shipment_count(base),
        n_cur=shipment_count(cur),
        contracted=steps[0][1],
        realised=steps[-1][1],
        waterfall=steps,
        effects=variance(base, cur),
        yours_pct=yours_pct,
        benchmark=bench,
        regimes=rate_regimes(lines),
        shuffle=detect_shuffle(lines),
    )


def to_dict(analysis: Analysis) -> dict:
    payload = asdict(analysis)
    payload["waterfall"] = [[label, value] for label, value in analysis.waterfall]
    if analysis.shuffle:
        payload["shuffle"] = {**analysis.shuffle, "pair": list(analysis.shuffle["pair"])}
    return payload


# common charge codes, spelled out so the reader never has to know the jargon
GLOSSARY = {
    "BAF": "fuel surcharge",
    "LSS": "low-sulphur fuel surcharge",
    "THC": "terminal handling",
    "PSS": "peak season surcharge",
    "DOC": "documentation fee",
    "CAF": "currency adjustment",
    "ISPS": "port security fee",
    "EBS": "emergency fuel surcharge",
    "AMS": "customs filing fee",
}

EFFECT_LABELS = {
    "volume": "Number of shipments (volume)",
    "price": "What carriers charged (price)",
    "mix": "Which lanes you used (mix)",
    "fx": "Exchange rates (FX)",
}


def _friendly_period(label: str) -> str:
    start, end = parse_period(label)
    if start.year == end.year:
        return f"{start.strftime('%b')}–{end.strftime('%b %Y')}"
    return f"{start.strftime('%b %Y')}–{end.strftime('%b %Y')}"


def _friendly_month(label: str) -> str:
    return pd.Period(label).to_timestamp().strftime("%b %Y")


def _step_label(label: str) -> str:
    spelled = GLOSSARY.get(label)
    return f"{label} — {spelled}" if spelled else label


def render(analysis: Analysis) -> None:
    console = Console()

    table = Table(title=f"What one shipment cost you, {_friendly_period(analysis.current)}")
    table.add_column("Step")
    table.add_column("$ / shipment", justify="right")
    for label, value in analysis.waterfall:
        anchor = label in ("Contracted base", "Realised all-in")
        text = f"{value:,.0f}" if anchor else f"{value:+,.0f}"
        table.add_row(_step_label(label), text, style="bold" if anchor else None)
    console.print(table)
    console.print(
        "Top row: the rate you negotiated. Bottom row: what you actually paid. "
        "Every line in between is a piece of the gap."
    )

    effects = Table(
        title=f"Why total spend changed, {_friendly_period(analysis.baseline)} → "
              f"{_friendly_period(analysis.current)}"
    )
    effects.add_column("Reason")
    effects.add_column("$", justify="right")
    for key in ("volume", "price", "mix", "fx"):
        effects.add_row(EFFECT_LABELS[key], f"{analysis.effects[key]:+,.0f}")
    effects.add_row("Total change", f"{analysis.effects['total_change']:+,.0f}", style="bold")
    console.print(effects)
    console.print("The four reasons add up to the total exactly — nothing is left over.")

    console.print(
        f"\nYour cost per shipment moved [bold]{analysis.yours_pct:+.1%}[/bold] "
        f"between the two periods ({analysis.n_base} shipments, then {analysis.n_cur})."
    )
    if analysis.benchmark:
        b = analysis.benchmark
        word = "better" if b["outperformance"] >= 0 else "worse"
        console.print(
            f"The market ({b['title']}) moved {b['market']:+.1%} over the same time. "
            f"You did [bold]{abs(b['outperformance']):.1%} points {word} than the "
            "market[/bold]."
        )

    for regime in analysis.regimes[:4]:
        console.print(
            f"Your all-in rate stepped {regime['step_pct']:+.1%} in "
            f"{_friendly_month(regime['month'])} "
            f"({regime['before']:,.0f} → {regime['after']:,.0f} per shipment)."
        )
    if analysis.shuffle:
        def prose(code: str) -> str:
            spelled = GLOSSARY.get(code)
            return f"{code} ({spelled})" if spelled else code

        a, b_code = analysis.shuffle["pair"]
        console.print(
            f"[yellow]Worth a look:[/yellow] {prose(a)} and {prose(b_code)} mirror "
            "each other month by month while their sum stays flat. That usually "
            "means money was relabelled between charge codes, not saved."
        )
