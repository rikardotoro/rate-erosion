import pandas as pd
from typer.testing import CliRunner

from rate_erosion.cli import app

runner = CliRunner()


def _files(tmp_path):
    rows = []
    for month, amt in (("2024-01", 1000), ("2024-02", 1000),
                       ("2025-01", 1080), ("2025-02", 1080)):
        for i in range(4):
            rows.append({"shipment": f"{month}-{i}", "date": f"{month}-10",
                         "lane": "A", "charge_code": "BAS", "amount": amt})
    lines = tmp_path / "lines.csv"
    pd.DataFrame(rows).to_csv(lines, index=False)
    contract = tmp_path / "contract.csv"
    pd.DataFrame([{"lane": "A", "base_rate": 1000}]).to_csv(contract, index=False)
    return lines, contract


def test_cli_runs_and_reports(tmp_path):
    lines, contract = _files(tmp_path)
    result = runner.invoke(app, [
        "--data", str(lines), "--contract", str(contract), "--benchmark", "none",
    ])
    assert result.exit_code == 0
    assert "Contracted base" in result.stdout


def test_cli_json_output_is_valid(tmp_path):
    import json

    lines, contract = _files(tmp_path)
    result = runner.invoke(app, [
        "--data", str(lines), "--contract", str(contract),
        "--benchmark", "none", "--json",
    ])
    assert result.exit_code == 0
    assert "waterfall" in json.loads(result.stdout)


def test_cli_refuses_baltic_dry(tmp_path):
    lines, contract = _files(tmp_path)
    result = runner.invoke(app, [
        "--data", str(lines), "--contract", str(contract), "--benchmark", "BDI",
    ])
    assert result.exit_code != 0
    assert "dry bulk" in result.stdout
