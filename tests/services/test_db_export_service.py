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


def test_db_export_service_filters_companies_to_current_run(tmp_path):
    db_path = tmp_path / "oie_test_filter.db"
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
                "company_key": "cmp_current",
                "company_display": "Current Co",
                "company_normalized": "current",
                "resolved_domain": "current.com",
                "domain_source": "apply_url",
                "domain_confidence": 0.95,
                "domain_candidate": "current.com",
                "domain_validation_status": "accepted",
                "domain_review_required": 0,
                "domain_ai_decision": "accepted",
                "industry": "Software",
                "employee_range": "11-50",
                "company_size": "11-50",
                "linkedin_company_url": "https://linkedin.com/company/current",
                "company_description": "Current run company",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.9,
                "aliases": ["Current Co"],
                "alias_type_map": {
                    "Current Co": "current",
                    "Current Co__type": "observed_name",
                },
                "opportunity_score": 30,
                "score_openings": 10,
                "score_remote": 8,
                "score_contractor": 4,
                "score_multi_source": 3,
                "score_company_type": 5,
            }
        ],
    )

    other_ctx = RunContext.create(
        config={
            "database": {"path": str(db_path)},
            "outputs": {"path": str(output_path)},
        },
        flags={},
    )
    other_persistence = PersistenceService(other_ctx)
    other_persistence.persist_run_snapshot(
        status="ok",
        companies=[
            {
                "company_key": "cmp_old",
                "company_display": "Old Co",
                "company_normalized": "old",
                "resolved_domain": "old.com",
                "domain_source": "apply_url",
                "domain_confidence": 0.91,
                "domain_candidate": "old.com",
                "domain_validation_status": "accepted",
                "domain_review_required": 0,
                "domain_ai_decision": "accepted",
                "industry": "Software",
                "employee_range": "51-200",
                "company_size": "51-200",
                "linkedin_company_url": "https://linkedin.com/company/old",
                "company_description": "Old run company",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.88,
                "aliases": ["Old Co"],
                "alias_type_map": {
                    "Old Co": "old",
                    "Old Co__type": "observed_name",
                },
                "opportunity_score": 99,
                "score_openings": 40,
                "score_remote": 20,
                "score_contractor": 20,
                "score_multi_source": 10,
                "score_company_type": 9,
            }
        ],
    )

    export_service = DBExportService(ctx)
    export_service.export_all()

    companies_text = Path(ctx.paths["companies_export"]).read_text(encoding="utf-8")

    assert "Current Co" in companies_text
    assert "current.com" in companies_text
    assert "accepted" in companies_text
    assert "end_client" in companies_text

    assert "Old Co" not in companies_text
    assert "old.com" not in companies_text
