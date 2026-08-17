"""Save the committable offline FRED slices: the two BLS producer price
indices (kept in full — monthly since 1988, a few KB) and the Fed's daily
EUR/USD rate (trimmed to the demo era; daily history would be large). All US
government data, public domain. The Cass index is proprietary and is never
committed, and never appears in a committed chart either."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rate_erosion.benchmark import fetch_series

EXAMPLES = Path(__file__).parent.parent / "src" / "rate_erosion" / "examples"
SLICES = {
    "PCU483111483111": None,          # full history — the README plots it
    "PCU4883204883208": None,         # full history — container handling PPI
    "DEXUSEU": "2020-01-01",          # daily; keep the demo era only
}


def main() -> int:
    for sid, since in SLICES.items():
        series = fetch_series(sid, EXAMPLES)  # cache file lands in examples/
        kept = series[series.index >= since] if since else series
        out = EXAMPLES / f"fred_{sid}.csv"
        kept.rename_axis("DATE").rename(sid).to_csv(out)
        (EXAMPLES / f"{sid}.csv").unlink()  # drop the raw cache, keep the slice
        print(f"{len(kept)} observations → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
