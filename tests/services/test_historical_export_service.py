from pathlib import Path
import json

from oie.orchestration.run_context import RunContext
from oie.services.historical_export_service import HistoricalExportService


def test_historical_export_service_writes_all_outputs(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )
    service = HistoricalExportService(ctx)

    rows = [
        {
            "company_key": "cmp_a",
            "company_display": "Acme Inc.",
            "jobs_total": 4,
            "growth_signal": "high",
        }
    ]

    company_history_path = service.export_company_history(rows)
    growth_summary_path = service.export_growth_summary(rows)
    summary_json_path = service.export_summary_json(rows)

    assert Path(company_history_path).exists()
    assert Path(growth_summary_path).exists()
    assert Path(summary_json_path).exists()

    assert ctx.paths["historical_company_hiring_csv"] == company_history_path
    assert ctx.paths["historical_growth_summary_csv"] == growth_summary_path
    assert ctx.paths["historical_summary_json"] == summary_json_path
    assert "output_dir" in ctx.paths
    assert Path(company_history_path).parent == Path(ctx.paths["output_dir"])
    assert Path(growth_summary_path).parent == Path(ctx.paths["output_dir"])
    assert Path(summary_json_path).parent == Path(ctx.paths["output_dir"])

    saved = json.loads(Path(summary_json_path).read_text(encoding="utf-8"))
    assert saved["run_id"] == ctx.run_id
    assert saved["companies_analyzed"] == 1
    assert saved["top_growing_companies"][0]["company_key"] == "cmp_a"
