from pathlib import Path
import csv
import json

from oie.orchestration.run_context import RunContext
from oie.services.collector_roi_export_service import CollectorROIExportService


def test_collector_roi_export_service_writes_csv_and_json(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )

    service = CollectorROIExportService(ctx)
    rows = [
        {
            "source": "linkedin_serpapi",
            "unique_jobs": 3,
            "duplicate_jobs": 1,
            "new_companies": 2,
            "leads_generated": 1,
            "utility_score": 8.5,
        }
    ]

    csv_path = service.export_csv(rows)
    json_path = service.export_json(rows)

    assert csv_path.endswith("collector_roi_metrics.csv")
    assert json_path.endswith("collector_roi_metrics.json")
    assert ctx.paths["collector_roi_metrics_csv"] == csv_path
    assert ctx.paths["collector_roi_metrics_json"] == json_path
    assert Path(csv_path).exists()
    assert Path(json_path).exists()

    with Path(csv_path).open("r", encoding="utf-8", newline="") as fh:
        saved_rows = list(csv.DictReader(fh))
    assert len(saved_rows) == 1
    assert saved_rows[0]["source"] == "linkedin_serpapi"
    assert saved_rows[0]["utility_score"] == "8.5"

    saved_json = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert len(saved_json) == 1
    assert saved_json[0]["source"] == "linkedin_serpapi"
    assert saved_json[0]["new_companies"] == 2
