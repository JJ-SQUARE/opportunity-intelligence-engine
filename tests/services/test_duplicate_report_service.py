from __future__ import annotations

from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.services.duplicate_report_service import DuplicateReportService


def test_duplicate_report_service_writes_csv(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )
    service = DuplicateReportService(ctx)

    output_path = service.write_suspected_duplicates_report(
        [
            {
                "entity_type": "job",
                "company": "Acme",
                "primary_value": "https://acme.com/jobs/1",
                "reason": "duplicate_against_master",
                "run_id": ctx.run_id,
                "run_date": ctx.run_date,
            }
        ]
    )

    assert Path(output_path).exists()
    assert ctx.metrics["suspected_duplicates_report_written"] == 1
