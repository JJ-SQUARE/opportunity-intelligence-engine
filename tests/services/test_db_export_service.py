from __future__ import annotations

from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.services.db_export_service import DBExportService
from oie.services.persistence_service import PersistenceService


def test_db_export_service_writes_csv_exports(tmp_path):
    db_path = tmp_path / "oie_test.db"
    output_path = tmp_path / "outputs"

    ctx = RunContext.create(
        config={
            "database": {"path": str(db_path)},
            "outputs": {"path": str(output_path)},
        },
        flags={},
    )

    persistence = PersistenceService(ctx)
    persistence.persist_run_snapshot(
        status="ok",
        companies=[
            {
                "company_key": "cmp_a",
                "company_display": "Acme Inc.",
                "company_normalized": "acme",
                "resolved_domain": "acme.com",
                "domain_source": "apply_url",
                "domain_confidence": 0.9,
                "aliases": ["Acme Inc."],
                "alias_type_map": {
                    "Acme Inc.": "acme",
                    "Acme Inc.__type": "observed_name",
                },
            }
        ],
        jobs=[
            {
                "title": "Backend Engineer",
                "company": "Acme Inc.",
                "company_key": "cmp_a",
                "location": "Remote",
                "job_url": "https://acme.com/jobs/1",
                "apply_url": "https://acme.com/apply/1",
                "description": "Python role",
                "source": "google_jobs",
                "detected_at": "2026-03-09",
            }
        ],
        leads=[
            {
                "company_key": "cmp_a",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "jane@acme.com",
                "linkedin_url": "https://linkedin.com/in/janedoe",
            }
        ],
    )

    export_service = DBExportService(ctx)
    export_service.export_all()

    assert Path(ctx.paths["companies_export"]).exists()
    assert Path(ctx.paths["jobs_export"]).exists()
    assert Path(ctx.paths["leads_export"]).exists()
