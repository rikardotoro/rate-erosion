"""Save the committable offline slice of the BLS PPI series (US government
data, public domain). The Cass index is proprietary and is never committed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rate_erosion.benchmark import fetch_series

EXAMPLES = Path(__file__).parent.parent / "examples"
SERIES_ID = "PCU483111483111"


def main() -> int:
    series = fetch_series(SERIES_ID, EXAMPLES)  # cache file lands in examples/
    kept = series[series.index >= "2020-01-01"]
    out = EXAMPLES / f"fred_{SERIES_ID}.csv"
    kept.rename_axis("DATE").rename(SERIES_ID).to_csv(out)
    (EXAMPLES / f"{SERIES_ID}.csv").unlink()  # drop the raw cache, keep the slice
    print(f"{len(kept)} observations → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
