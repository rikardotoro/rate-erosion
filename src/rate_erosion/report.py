from dataclasses import asdict, dataclass

import pandas as pd
from rich.console import Console
from rich.table import Table

from rate_erosion.benchmark import pct_change, verdict
from rate_erosion.data import parse_period, split_periods
from rate_erosion.decompose import converted, shipment_count, variance, waterfall


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
    )


def to_dict(analysis: Analysis) -> dict:
    payload = asdict(analysis)
    payload["waterfall"] = [[label, value] for label, value in analysis.waterfall]
    return payload


def render(analysis: Analysis) -> None:
    console = Console()

    table = Table(title=f"Per shipment, {analysis.current}")
    table.add_column("Step")
    table.add_column("$ / shipment", justify="right")
    for label, value in analysis.waterfall:
        anchor = label in ("Contracted base", "Realised all-in")
        text = f"{value:,.0f}" if anchor else f"{value:+,.0f}"
        table.add_row(label, text, style="bold" if anchor else None)
    console.print(table)

    effects = Table(title="Total spend change")
    effects.add_column("Effect")
    effects.add_column("$", justify="right")
    for key in ("volume", "price", "mix", "fx"):
        effects.add_row(key.capitalize(), f"{analysis.effects[key]:+,.0f}")
    effects.add_row("Total", f"{analysis.effects['total_change']:+,.0f}", style="bold")
    console.print(effects)

    console.print(
        f"\nRealised cost per shipment moved [bold]{analysis.yours_pct:+.1%}[/bold] "
        f"({analysis.n_base} shipments in {analysis.baseline}, "
        f"{analysis.n_cur} in {analysis.current})."
    )
    if analysis.benchmark:
        b = analysis.benchmark
        word = "outperformed" if b["outperformance"] >= 0 else "underperformed"
        console.print(
            f"The market ({b['title']}) moved {b['market']:+.1%} over the same window "
            f"— you [bold]{word} by {abs(b['outperformance']):.1%} points[/bold]."
        )
