"""Regenerate the README charts from the demo data so they can never drift from behaviour.

Writes light and dark SVG variants to docs/charts/. No plotting library:
the charts are plain SVG, so the repo's only dependencies stay the runtime four.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rate_erosion.benchmark import fill_fx, load_series
from rate_erosion.data import load_contract, load_cost_lines, split_periods
from rate_erosion.decompose import converted, waterfall
from rate_erosion.patterns import monthly_matrix

ROOT = Path(__file__).parent.parent
OUT = ROOT / "docs" / "charts"

FONT = "system-ui, -apple-system, Segoe UI, sans-serif"

# Palette validated for both GitHub surfaces (#ffffff / #0d1117):
# blue = contracted/market (the reference), orange = erosion/you (the evidence).
TOKENS = {
    "light": {
        "anchor": "#2a78d6", "erosion": "#eb6834",
        "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
        "grid": "#e1e0d9", "axis": "#c3c2b7",
    },
    "dark": {
        "anchor": "#3987e5", "erosion": "#d95926",
        "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#898781",
        "grid": "#2c2c2a", "axis": "#383835",
    },
}


def _text(x, y, s, size, fill, anchor="start", weight="normal", tabular=False):
    style = "font-variant-numeric: tabular-nums;" if tabular else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
        f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" style="{style}">{s}</text>'
    )


def _line(x1, y1, x2, y2, stroke, width=1.0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width}"{d}/>'
    )


def _svg(width, height, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n' + "\n".join(body) + "\n</svg>\n"
    )


# ---------------------------------------------------------------- chart 1
def chart_waterfall(lines, contract, mode):
    t = TOKENS[mode]
    _, cur, _, cur_label = split_periods(lines)
    steps = waterfall(cur, contract)

    W, H = 760, 370
    left, right, top, bottom = 52, 26, 74, 60
    x0, x1, y0, y1 = left, W - right, H - bottom, top + 14
    top_value = max(steps[0][1], steps[-1][1]) * 1.12
    slot = (x1 - x0) / len(steps)
    bar_w = slot * 0.58

    def Y(v):
        return y0 - v / top_value * (y0 - y1)

    body = [_text(20, 26, "Where the negotiated rate went", 16, t["ink"], weight="600"),
            _text(20, 44, f"Per-shipment cost build-up over {cur_label}, the last quarter of the demo contract.",
                  12, t["ink2"])]

    for v in range(0, int(top_value) + 1, 500):
        body.append(_line(x0, Y(v), x1, Y(v), t["grid"]))
        body.append(_text(x0 - 8, Y(v) + 4, f"{v:,}", 11, t["muted"], anchor="end", tabular=True))

    running = steps[0][1]
    for index, (label, value) in enumerate(steps):
        cx = x0 + (index + 0.5) * slot
        anchor_bar = index == 0 or index == len(steps) - 1
        if anchor_bar:
            lo, hi, color = 0.0, value, t["anchor"]
        else:
            lo, hi = sorted((running, running + value))
            color = t["erosion"]
            running += value
        body.append(f'<rect x="{cx - bar_w / 2:.1f}" y="{Y(hi):.1f}" width="{bar_w:.1f}" '
                    f'height="{max(Y(lo) - Y(hi), 2):.1f}" rx="3" fill="{color}"/>')
        if not anchor_bar:
            # connector from the previous bar's top level into this step
            body.append(_line(cx - slot + bar_w / 2, Y(lo if value >= 0 else hi),
                              cx - bar_w / 2, Y(lo if value >= 0 else hi),
                              t["muted"], 1.0, dash="2 2"))
        if index == len(steps) - 1:
            body.append(_line(cx - slot + bar_w / 2, Y(running),
                              cx - bar_w / 2, Y(running), t["muted"], 1.0, dash="2 2"))
        shown = f"{value:,.0f}" if anchor_bar else f"{value:+,.0f}"
        body.append(_text(cx, Y(hi) - 7, shown, 11,
                          t["ink"] if anchor_bar else t["erosion"],
                          anchor="middle", weight="600", tabular=True))
        words = label.split()
        for k, word in enumerate(words):
            body.append(_text(cx, y0 + 16 + k * 13, word, 10, t["muted"], anchor="middle"))

    body.append(_line(x0, y0, x1, y0, t["axis"], 1.2))
    return _svg(W, H, body)


# ---------------------------------------------------------------- chart 2
def chart_market(lines, market, mode):
    t = TOKENS[mode]
    month = lines["date"].dt.to_period("M")
    monthly = converted(lines).groupby(month).sum() / lines.groupby(month)["shipment"].nunique()
    yours = monthly / monthly.iloc[0] * 100.0
    span = [p.to_timestamp() for p in yours.index]

    fred = market.sort_index()
    fred = fred[(fred.index >= span[0]) & (fred.index <= span[-1] + pd.offsets.MonthEnd(0))]
    fred = fred / fred.iloc[0] * 100.0

    W, H = 760, 340
    left, right, top, bottom = 52, 150, 74, 40
    x0, x1, y0, y1 = left, W - right, H - bottom, top + 6
    lo = min(yours.min(), fred.min()) - 4
    hi = max(yours.max(), fred.max()) + 6

    def X(ts):
        return x0 + (ts - span[0]) / (span[-1] - span[0]) * (x1 - x0)

    def Y(v):
        return y0 - (v - lo) / (hi - lo) * (y0 - y1)

    body = [_text(20, 26, "Your cost vs the market", 16, t["ink"], weight="600"),
            _text(20, 44, "Indexed to 100 at the start of the demo contract. The gap is the outperformance.",
                  12, t["ink2"])]

    for v in range(int(lo // 10 * 10) + 10, int(hi) + 1, 10):
        body.append(_line(x0, Y(v), x1, Y(v), t["grid"]))
        body.append(_text(x0 - 8, Y(v) + 4, f"{v}", 11, t["muted"], anchor="end", tabular=True))

    def path(points, color):
        d = " L ".join(f"{x:.1f} {y:.1f}" for x, y in points)
        return (f'<path d="M {d}" fill="none" stroke="{color}" stroke-width="2" '
                f'stroke-linejoin="round"/>')

    body.append(path([(X(ts), Y(v)) for ts, v in zip(span, yours)], t["erosion"]))
    body.append(path([(X(ts), Y(v)) for ts, v in fred.items()], t["anchor"]))

    body.append(_text(x1 + 10, Y(fred.iloc[-1]) + 4, f"market {fred.iloc[-1]:.0f}", 12,
                      t["anchor"], weight="600", tabular=True))
    body.append(_text(x1 + 10, Y(yours.iloc[-1]) + 4, f"you {yours.iloc[-1]:.0f}", 12,
                      t["erosion"], weight="600", tabular=True))

    for ts in span[::3]:
        body.append(_text(X(ts), y0 + 18, ts.strftime("%b %y"), 11, t["muted"],
                          anchor="middle", tabular=True))
    body.append(_line(x0, y0, x1, y0, t["axis"], 1.2))
    return _svg(W, H, body)


# ---------------------------------------------------------------- chart 3
def chart_relabel(lines, mode):
    t = TOKENS[mode]
    matrix = monthly_matrix(lines)
    baf, lss = matrix["BAF"], matrix.get("LSS", matrix["BAF"] * 0.0)
    together = baf + lss
    span = [p.to_timestamp() for p in matrix.index]

    W, H = 760, 300
    left, right, top, bottom = 52, 130, 74, 40
    x0, x1, y0, y1 = left, W - right, H - bottom, top + 6
    hi = float(together.max()) * 1.15

    def X(ts):
        return x0 + (ts - span[0]) / (span[-1] - span[0]) * (x1 - x0)

    def Y(v):
        return y0 - v / hi * (y0 - y1)

    body = [_text(20, 26, "Money moved codes, not size", 16, t["ink"], weight="600"),
            _text(20, 44, "Monthly bunker charge per shipment in the demo. In October a new code appears; the sum does not care.",
                  12, t["ink2"])]

    for v in range(0, int(hi) + 1, 100):
        body.append(_line(x0, Y(v), x1, Y(v), t["grid"]))
        body.append(_text(x0 - 8, Y(v) + 4, f"{v}", 11, t["muted"], anchor="end", tabular=True))

    def path(series, color, dash=None):
        d = " L ".join(f"{X(ts):.1f} {Y(float(v)):.1f}" for ts, v in zip(span, series))
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        return (f'<path d="M {d}" fill="none" stroke="{color}" stroke-width="2" '
                f'stroke-linejoin="round"{extra}/>')

    body.append(path(together, t["ink2"], dash="5 4"))
    body.append(path(baf, t["anchor"]))
    body.append(path(lss, t["erosion"]))

    body.append(_text(x1 + 10, Y(float(together.iloc[-1])) + 4, "BAF + LSS", 12, t["ink2"], weight="600"))
    body.append(_text(x1 + 10, Y(float(baf.iloc[-1])) + 4, "BAF", 12, t["anchor"], weight="600"))
    body.append(_text(x1 + 10, Y(float(lss.iloc[-1])) + 4, "LSS", 12, t["erosion"], weight="600"))

    for ts in span[::3]:
        body.append(_text(X(ts), y0 + 18, ts.strftime("%b %y"), 11, t["muted"],
                          anchor="middle", tabular=True))
    body.append(_line(x0, y0, x1, y0, t["axis"], 1.2))
    return _svg(W, H, body)


# ---------------------------------------------------------------- chart 4
def chart_history(market, mode):
    """38 years of the deep-sea PPI, with the demo contract window shaded."""
    t = TOKENS[mode]
    series = market.sort_index()
    w_start, w_end = pd.Timestamp("2021-01-01"), pd.Timestamp("2022-06-30")

    W, H = 760, 300
    left, right, top, bottom = 52, 26, 74, 40
    x0, x1, y0, y1 = left, W - right, H - bottom, top + 6
    lo, hi = 0.0, float(series.max()) * 1.08

    def X(ts):
        return x0 + (ts - series.index[0]) / (series.index[-1] - series.index[0]) * (x1 - x0)

    def Y(v):
        return y0 - (v - lo) / (hi - lo) * (y0 - y1)

    body = [_text(20, 26, "The survey has seen everything", 16, t["ink"], weight="600"),
            _text(20, 44, "The Deep Sea Freight producer price index, monthly since 1988. The shaded band is the demo contract.",
                  12, t["ink2"])]

    for v in range(0, int(hi) + 1, 100):
        body.append(_line(x0, Y(v), x1, Y(v), t["grid"]))
        body.append(_text(x0 - 8, Y(v) + 4, f"{v}", 11, t["muted"], anchor="end", tabular=True))

    body.append(f'<rect x="{X(w_start):.1f}" y="{y1:.1f}" width="{X(w_end) - X(w_start):.1f}" '
                f'height="{y0 - y1:.1f}" fill="{t["erosion"]}" fill-opacity="0.15"/>')
    body.append(_text((X(w_start) + X(w_end)) / 2, y1 + 14, "the demo", 11,
                      t["erosion"], anchor="middle", weight="600"))

    d = " L ".join(f"{X(ts):.1f} {Y(float(v)):.1f}" for ts, v in series.items())
    body.append(f'<path d="M {d}" fill="none" stroke="{t["anchor"]}" stroke-width="2" '
                f'stroke-linejoin="round"/>')

    for year in range(1990, 2027, 5):
        ts = pd.Timestamp(f"{year}-01-01")
        body.append(_text(X(ts), y0 + 18, str(year), 11, t["muted"], anchor="middle", tabular=True))
    body.append(_line(x0, y0, x1, y0, t["axis"], 1.2))
    return _svg(W, H, body)


# ---------------------------------------------------------------- chart 5
def chart_benchmarks(lines, deep_sea, handling, mode):
    """Two free surveys, two very different markets — plus you, over the term."""
    t = TOKENS[mode]
    aqua = "#1baf7a" if mode == "light" else "#199e70"

    month = lines["date"].dt.to_period("M")
    monthly = converted(lines).groupby(month).sum() / lines.groupby(month)["shipment"].nunique()
    yours = monthly / monthly.iloc[0] * 100.0
    span = [p.to_timestamp() for p in yours.index]

    def indexed(series):
        picked = series.sort_index()
        picked = picked[(picked.index >= span[0]) & (picked.index <= span[-1] + pd.offsets.MonthEnd(0))]
        return picked / picked.iloc[0] * 100.0

    sea, port = indexed(deep_sea), indexed(handling)

    W, H = 760, 340
    left, right, top, bottom = 52, 200, 74, 40
    x0, x1, y0, y1 = left, W - right, H - bottom, top + 6
    lo = min(yours.min(), sea.min(), port.min()) - 4
    hi = max(yours.max(), sea.max(), port.max()) + 6

    def X(ts):
        return x0 + (ts - span[0]) / (span[-1] - span[0]) * (x1 - x0)

    def Y(v):
        return y0 - (v - lo) / (hi - lo) * (y0 - y1)

    body = [_text(20, 26, "Pick the market you actually buy", 16, t["ink"], weight="600"),
            _text(20, 44, "Both are free government surveys, indexed to 100. They are not the same market.",
                  12, t["ink2"])]

    for v in range(int(lo // 10 * 10) + 10, int(hi) + 1, 10):
        body.append(_line(x0, Y(v), x1, Y(v), t["grid"]))
        body.append(_text(x0 - 8, Y(v) + 4, f"{v}", 11, t["muted"], anchor="end", tabular=True))

    def path(points, color):
        d = " L ".join(f"{x:.1f} {y:.1f}" for x, y in points)
        return (f'<path d="M {d}" fill="none" stroke="{color}" stroke-width="2" '
                f'stroke-linejoin="round"/>')

    body.append(path([(X(ts), Y(v)) for ts, v in sea.items()], t["anchor"]))
    body.append(path([(X(ts), Y(v)) for ts, v in port.items()], aqua))
    body.append(path([(X(ts), Y(v)) for ts, v in zip(span, yours)], t["erosion"]))

    body.append(_text(x1 + 10, Y(float(sea.iloc[-1])) + 4,
                      f"ocean freight {sea.iloc[-1]:.0f}", 12, t["anchor"], weight="600"))
    body.append(_text(x1 + 10, Y(float(yours.iloc[-1])) + 4,
                      f"you {yours.iloc[-1]:.0f}", 12, t["erosion"], weight="600"))
    body.append(_text(x1 + 10, Y(float(port.iloc[-1])) - 8,
                      f"port handling {port.iloc[-1]:.0f}", 12, aqua, weight="600"))

    for ts in span[::3]:
        body.append(_text(X(ts), y0 + 18, ts.strftime("%b %y"), 11, t["muted"],
                          anchor="middle", tabular=True))
    body.append(_line(x0, y0, x1, y0, t["axis"], 1.2))
    return _svg(W, H, body)


def main() -> int:
    lines = load_cost_lines(ROOT / "examples" / "demo.csv")
    lines = fill_fx(lines, ROOT / "examples", offline_dir=ROOT / "examples")
    contract = load_contract(ROOT / "examples" / "contract.csv")
    market = load_series(ROOT / "examples" / "fred_PCU483111483111.csv")
    handling = load_series(ROOT / "examples" / "fred_PCU4883204883208.csv")
    OUT.mkdir(parents=True, exist_ok=True)
    for mode in ("light", "dark"):
        (OUT / f"waterfall-{mode}.svg").write_text(chart_waterfall(lines, contract, mode))
        (OUT / f"market-{mode}.svg").write_text(chart_market(lines, market, mode))
        (OUT / f"relabel-{mode}.svg").write_text(chart_relabel(lines, mode))
        (OUT / f"history-{mode}.svg").write_text(chart_history(market, mode))
        (OUT / f"benchmarks-{mode}.svg").write_text(chart_benchmarks(lines, market, handling, mode))
        print(f"wrote {mode} charts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
