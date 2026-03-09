from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.services.outbound_export_service import OutboundExportService
from oie.services.persistence_service import PersistenceService


def test_outbound_export_service_writes_files(tmp_path):
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
                "industry": "Software",
                "employee_range": "51-200",
                "linkedin_company_url": "https://linkedin.com/company/acme",
                "company_description": "Builds software",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.9,
                "classification_provider": "rules",
                "aliases": ["Acme Inc."],
                "alias_type_map": {
                    "Acme Inc.": "acme",
                    "Acme Inc.__type": "observed_name",
                },
                "opportunity_score": 42,
                "score_openings": 16,
                "score_remote": 8,
                "score_contractor": 6,
                "score_multi_source": 10,
                "score_company_type": 2,
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
                "lead_source": "apollo_people",
                "lead_confidence": 0.9,
            }
        ],
    )

    service = OutboundExportService(ctx)
    service.export_all()

    assert Path(ctx.paths["apollo_import_csv"]).exists()
    assert Path(ctx.paths["top_opportunities_csv"]).exists()
    assert Path(ctx.paths["end_clients_csv"]).exists()
    assert Path(ctx.paths["vendors_csv"]).exists()
    assert Path(ctx.paths["marketplaces_csv"]).exists()
