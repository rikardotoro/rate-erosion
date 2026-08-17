import subprocess
import sys
from pathlib import Path

from rate_erosion.benchmark import load_series
from rate_erosion.data import load_contract, load_cost_lines

EXAMPLES = Path(__file__).parent.parent / "src" / "rate_erosion" / "examples"


def test_demo_files_are_small():
    total = sum(f.stat().st_size for f in EXAMPLES.glob("*.csv"))
    assert total < 1_000_000


def test_demo_loads_and_spans_the_contract_term():
    lines = load_cost_lines(EXAMPLES / "demo.csv")
    assert lines["shipment"].nunique() > 500
    assert lines["date"].dt.to_period("M").nunique() == 18
    assert set(lines["currency"]) == {"USD", "EUR"}
    load_contract(EXAMPLES / "contract.csv")  # must not raise


def test_demo_is_reproducible():
    subprocess.run(
        [sys.executable, "scripts/make_demo.py"],
        capture_output=True, text=True, check=True,
        cwd=EXAMPLES.parent.parent.parent,
    )
    diff = subprocess.run(
        ["git", "diff", "--exit-code", "--",
         "src/rate_erosion/examples/demo.csv", "src/rate_erosion/examples/contract.csv"],
        cwd=EXAMPLES.parent.parent.parent, capture_output=True,
    )
    assert diff.returncode == 0, "regenerating the demo must produce no git diff"


def test_offline_fred_slice_loads():
    series = load_series(EXAMPLES / "fred_PCU483111483111.csv")
    assert len(series) > 24


def test_demo_shuffle_is_detected():
    """The planted BAF-to-LSS relabelling must be caught on the demo data."""
    from rate_erosion.benchmark import fill_fx
    from rate_erosion.patterns import detect_shuffle

    lines = load_cost_lines(EXAMPLES / "demo.csv")
    lines = fill_fx(lines, EXAMPLES, offline_dir=EXAMPLES)
    result = detect_shuffle(lines)
    assert result is not None
    assert set(result["pair"]) == {"BAF", "LSS"}
