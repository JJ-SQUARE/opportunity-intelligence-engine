from pathlib import Path
import json

from oie.orchestration.run_context import RunContext
from oie.services.market_trends_export_service import MarketTrendsExportService


def test_market_trends_export_service_writes_all_outputs(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )
    service = MarketTrendsExportService(ctx)

    source_rows = [
        {"source": "google_jobs", "jobs_count": 5, "companies_count": 2}
    ]
    location_rows = [
        {"location": "Mexico", "jobs_count": 3, "companies_count": 2}
    ]
    new_companies_rows = [
        {"source": "linkedin_serpapi", "new_companies_count": 2}
    ]
    summary_payload = {
        "run_id": ctx.run_id,
        "totals": {"jobs": 5, "companies": 2},
    }

    source_path = service.export_source_trends(source_rows)
    location_path = service.export_country_trends(location_rows)
    new_companies_path = service.export_new_companies_by_source(new_companies_rows)
    summary_path = service.export_summary_json(summary_payload)

    assert Path(source_path).exists()
    assert Path(location_path).exists()
    assert Path(new_companies_path).exists()
    assert Path(summary_path).exists()

    assert ctx.paths["market_trends_by_source_csv"] == source_path
    assert ctx.paths["market_trends_by_location_csv"] == location_path
    assert ctx.paths["market_new_companies_by_source_csv"] == new_companies_path
    assert ctx.paths["market_trends_summary_json"] == summary_path

    saved = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    assert saved["run_id"] == ctx.run_id
    assert saved["totals"]["jobs"] == 5
