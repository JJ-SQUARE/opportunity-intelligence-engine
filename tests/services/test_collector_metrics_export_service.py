from pathlib import Path
import json

from oie.orchestration.run_context import RunContext
from oie.services.collector_metrics_export_service import CollectorMetricsExportService


def test_collector_metrics_export_service_writes_json(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )

    service = CollectorMetricsExportService(ctx)
    metrics = [
        {
            "source": "google_jobs",
            "jobs_collected": 2,
            "unique_companies": 1,
            "jobs_per_company": 2.0,
        }
    ]

    out_path = service.export_json(metrics)

    assert out_path.endswith("collector_metrics.json")
    assert ctx.paths["collector_metrics_json"] == out_path
    assert Path(out_path).exists()

    saved = json.loads(Path(out_path).read_text(encoding="utf-8"))
    assert saved[0]["source"] == "google_jobs"
    assert saved[0]["jobs_collected"] == 2
