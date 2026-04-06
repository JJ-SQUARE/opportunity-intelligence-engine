from pathlib import Path
import json

from oie.orchestration.run_context import RunContext
from oie.services.market_segmentation_export_service import MarketSegmentationExportService


def test_market_segmentation_export_service_writes_all_outputs(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )
    service = MarketSegmentationExportService(ctx)

    segmented_rows = [
        {
            "company_key": "cmp_a",
            "company_display": "Acme Inc.",
            "segment": "end_client",
        }
    ]
    summary_rows = [
        {
            "segment": "end_client",
            "companies_count": 1,
        }
    ]

    segmented_path = service.export_segmented_companies(segmented_rows)
    summary_csv_path = service.export_segment_summary(summary_rows)
    summary_json_path = service.export_segment_summary_json(summary_rows)

    assert Path(segmented_path).exists()
    assert Path(summary_csv_path).exists()
    assert Path(summary_json_path).exists()

    assert ctx.paths["market_segmented_companies_csv"] == segmented_path
    assert ctx.paths["market_segment_summary_csv"] == summary_csv_path
    assert ctx.paths["market_segment_summary_json"] == summary_json_path

    saved = json.loads(Path(summary_json_path).read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["segment"] == "end_client"
