import pandas as pd
import pytest

from rate_erosion.report import analyse, to_dict


def _lines() -> pd.DataFrame:
    rows = []
    for month, base_amt, baf in (("2024-01", 1000, 200), ("2024-02", 1000, 200),
                                 ("2025-01", 1050, 320), ("2025-02", 1050, 320)):
        for i in range(5):
            sid = f"{month}-{i}"
            rows.append({"shipment": sid, "date": f"{month}-10", "lane": "A",
                         "charge_code": "BAS", "amount": base_amt})
            rows.append({"shipment": sid, "date": f"{month}-10", "lane": "A",
                         "charge_code": "BAF", "amount": baf})
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"])
    frame["currency"] = "USD"
    frame["fx_rate"] = 1.0
    return frame


CONTRACT = pd.DataFrame({"lane": ["A"], "base_rate": [1000.0]})


def test_analysis_counts_and_change():
    analysis = analyse(_lines(), CONTRACT, "2024-01:2024-02", "2025-01:2025-02",
                       market=None, market_title=None)
    assert analysis.n_base == 10 and analysis.n_cur == 10
    # 1200 -> 1370 per shipment
    assert analysis.yours_pct == pytest.approx(170 / 1200)
    assert analysis.benchmark is None


def test_verdict_included_when_market_given():
    market = pd.Series([100.0, 130.0],
                       index=pd.to_datetime(["2024-01-01", "2025-02-01"]))
    analysis = analyse(_lines(), CONTRACT, "2024-01:2024-02", "2025-01:2025-02",
                       market=market, market_title="PPI test")
    assert analysis.benchmark["market"] == pytest.approx(0.30)
    assert analysis.benchmark["outperformance"] == pytest.approx(0.30 - 170 / 1200)


def test_to_dict_is_json_serialisable():
    import json

    analysis = analyse(_lines(), CONTRACT, None, None, market=None, market_title=None)
    json.dumps(to_dict(analysis))  # must not raise
