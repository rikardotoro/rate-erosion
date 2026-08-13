"""Save the committable offline FRED slices: the BLS PPI benchmark and the
Fed's daily EUR/USD rate (both US government data, public domain). The Cass
index is proprietary and is never committed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rate_erosion.benchmark import fetch_series

EXAMPLES = Path(__file__).parent.parent / "examples"
SLICES = ("PCU483111483111", "DEXUSEU")


def main() -> int:
    for sid in SLICES:
        series = fetch_series(sid, EXAMPLES)  # cache file lands in examples/
        kept = series[series.index >= "2020-01-01"]
        out = EXAMPLES / f"fred_{sid}.csv"
        kept.rename_axis("DATE").rename(sid).to_csv(out)
        (EXAMPLES / f"{sid}.csv").unlink()  # drop the raw cache, keep the slice
        print(f"{len(kept)} observations → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
