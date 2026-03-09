from __future__ import annotations

from oie.orchestration.run_context import RunContext
from oie.services.master_data_service import MasterDataService


def test_master_data_service_appends_jobs_with_run_metadata(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    service = MasterDataService(ctx)

    count = service.append_jobs(
        [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "job_url": "https://acme.com/jobs/1",
                "apply_url": "https://acme.com/apply/1",
                "description": "Python role",
                "source": "google_jobs",
                "detected_at": "2026-03-09",
            }
        ]
    )

    rows = service.read_master_rows("jobs")

    assert count == 1
    assert rows[0]["title"] == "Backend Engineer"
    assert rows[0]["run_id"] == ctx.run_id


def test_master_data_service_skips_write_on_schema_mismatch(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    service = MasterDataService(ctx)

    service.append_entity_rows(
        "jobs",
        [{"foo": "bar"}],
        ["foo"],
    )

    count = service.safe_append_entity_rows(
        "jobs",
        [{"title": "Backend Engineer"}],
        ["title", "run_id", "run_date"],
    )

    assert count == 0
    assert ctx.metrics["master_jobs_write_skipped_schema_error"] is True
