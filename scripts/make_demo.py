"""Generate the synthetic demo data. Committed because it IS the data source.

The data is synthetic and says so in examples/SOURCE.md. Real invoice-level
freight cost data is never published; the FRED market benchmark is real.
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent.parent / "examples"

LANES = {"CNSHA-USLAX": 1950.0, "CNSHA-NLRTM": 2450.0}  # contracted base, USD
MONTHS = pd.period_range("2021-01", "2022-06", freq="M")
PSS_MONTHS = {"2021-08", "2021-09", "2021-10", "2022-04", "2022-05", "2022-06"}


def main() -> int:
    rng = np.random.default_rng(2026)
    rows = []
    n_months = len(MONTHS)

    for m_index, month in enumerate(MONTHS):
        t = m_index / (n_months - 1)                     # 0 → 1 over the term
        mix_dear = 0.35 + t * 0.20                       # NLRTM share 35% → 55%
        baf = 380.0 + t * 80.0                           # bunker creep
        creep = 1.0 + t * 0.025                          # base over-billing 0 → 2.5%

        # the shuffle: from 2021-10 a "new" LSS code appears while BAF drops by
        # the same amount — the all-in is untouched, money just changes labels
        lss = 130.0 if m_index >= 9 else 0.0

        for i in range(rng.integers(55, 66)):
            lane = "CNSHA-NLRTM" if rng.random() < mix_dear else "CNSHA-USLAX"
            sid = f"{month}-{i:03d}"
            date = pd.Timestamp(month.start_time) + pd.Timedelta(days=int(rng.integers(0, 28)))

            def line(code, amount, currency="USD"):
                # fx_rate is deliberately absent: the tool fills it from the
                # Fed's real daily rates (see benchmark.fill_fx)
                rows.append({"shipment": sid, "date": date.date(), "lane": lane,
                             "charge_code": code, "amount": round(float(amount), 2),
                             "currency": currency})

            line("BAS", LANES[lane] * creep * rng.normal(1.0, 0.01))
            line("BAF", (baf - lss) * rng.normal(1.0, 0.05))
            if lss:
                line("LSS", lss * rng.normal(1.0, 0.03))
            line("THC", 220.0 * rng.normal(1.0, 0.03), currency="EUR")
            line("DOC", 45.0)
            if str(month) in PSS_MONTHS:
                line("PSS", 200.0)

    frame = pd.DataFrame(rows).sort_values(["date", "shipment"]).reset_index(drop=True)
    OUT.mkdir(exist_ok=True)
    frame.to_csv(OUT / "demo.csv", index=False)
    pd.DataFrame(
        [{"lane": lane, "base_rate": rate} for lane, rate in LANES.items()]
    ).to_csv(OUT / "contract.csv", index=False)
    print(f"{len(frame)} cost lines, {frame['shipment'].nunique()} shipments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
