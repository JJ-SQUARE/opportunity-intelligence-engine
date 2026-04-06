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
            "market_segment": "tech_product_hiring",
        }
    ]
    summary_rows = [
        {
            "market_segment": "tech_product_hiring",
            "companies": 1,
            "avg_score": 84.0,
            "avg_vendor_prob": 0.0,
            "top_examples": "Acme Inc.",
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

    assert "output_dir" in ctx.paths
    assert Path(segmented_path).parent == Path(ctx.paths["output_dir"])
    assert Path(summary_csv_path).parent == Path(ctx.paths["output_dir"])
    assert Path(summary_json_path).parent == Path(ctx.paths["output_dir"])

    saved = json.loads(Path(summary_json_path).read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["market_segment"] == "tech_product_hiring"
    assert saved[0]["companies"] == 1
