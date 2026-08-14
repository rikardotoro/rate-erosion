import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from rate_erosion.benchmark import (USDA_ID, SERIES, fetch_series, fetch_usda,
                                    fill_fx, load_series, resolve_series)
from rate_erosion.data import load_contract, load_cost_lines
from rate_erosion.errors import RateErosionError
from rate_erosion.report import analyse, render, to_dict

app = typer.Typer(add_completion=False, help="Where your negotiated rate actually went.")
console = Console()

EXAMPLES = Path(__file__).parent.parent.parent / "examples"
CACHE = Path.home() / ".cache" / "rate-erosion"


@app.command()
def main(
    data: Annotated[Path | None, typer.Option(help="Cost lines CSV.")] = None,
    contract: Annotated[Path | None, typer.Option(help="Contract CSV: lane, base_rate.")] = None,
    demo: Annotated[bool, typer.Option(help="Use the bundled synthetic example.")] = False,
    baseline: Annotated[str | None, typer.Option(help="YYYY-MM:YYYY-MM.")] = None,
    current: Annotated[str | None, typer.Option(help="YYYY-MM:YYYY-MM.")] = None,
    benchmark: Annotated[str, typer.Option(help="FRED series id, or 'none'.")] = "PCU483111483111",
    map_: Annotated[list[str] | None, typer.Option("--map", help="canonical=column")] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    if demo:
        data = data or EXAMPLES / "demo.csv"
        contract = contract or EXAMPLES / "contract.csv"
    if data is None or contract is None:
        raise typer.BadParameter("provide --data and --contract, or --demo")

    overrides = dict(item.split("=", 1) for item in (map_ or []))

    try:
        lines = load_cost_lines(data, overrides or None)
        if lines["fx_rate"].isna().any():
            lines = fill_fx(lines, CACHE, offline_dir=EXAMPLES if demo else None)
        agreement = load_contract(contract)

        market = market_title = None
        if benchmark.lower() != "none":
            series_id = resolve_series(benchmark)
            offline = EXAMPLES / f"fred_{series_id}.csv"
            if series_id == USDA_ID:
                market = fetch_usda(CACHE)  # fetch-only: Drewry attribution
            elif demo and offline.exists():
                market = load_series(offline)
            else:
                market = fetch_series(series_id, CACHE)
            market_title = SERIES[series_id]

        analysis = analyse(lines, agreement, baseline, current, market, market_title)
    except RateErosionError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error

    if as_json:
        print(json.dumps(to_dict(analysis), indent=2))
    else:
        render(analysis)


if __name__ == "__main__":
    app()
