import csv
from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.services.opportunity_dataset_export_service import OpportunityDatasetExportService
from oie.services.opportunity_dataset_service import OpportunityDatasetService
from oie.services.persistence_service import PersistenceService


def test_opportunity_dataset_service_builds_dataset_and_exports(tmp_path):
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
                "industry": "Software",
                "employee_range": "51-200",
                "linkedin_company_url": "https://linkedin.com/company/acme",
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
                "email_quality_score": 95,
                "lead_capture_reason": "apollo_match | title:CTO | email_quality:95",
                "lead_relevance_score": 197,
            },
            {
                "company_key": "cmp_a",
                "contact_name": "John Roe",
                "contact_title": "VP Engineering",
                "email": "",
                "linkedin_url": "https://linkedin.com/in/johnroe",
                "lead_source": "hunter_domain_search",
                "lead_confidence": 0.7,
                "email_quality_score": 70,
                "lead_capture_reason": "hunter_match | title:VP Engineering | email_quality:70",
                "lead_relevance_score": 160,
            }
        ],
    )

    dataset_service = OpportunityDatasetService(ctx)
    export_service = OpportunityDatasetExportService(ctx)

    dataset = dataset_service.build_dataset()
    top_dataset = dataset_service.build_top_opportunities(limit=10)

    export_service.export_dataset(dataset)
    export_service.export_top_dataset(top_dataset)

    assert len(dataset) == 1
    assert dataset[0]["company_key"] == "cmp_a"
    assert dataset[0]["jobs_count"] == 1
    assert dataset[0]["email"] == "jane@acme.com"
    assert dataset[0]["opportunity_score"] == 42
    assert dataset[0]["industry"] == "Software"
    assert dataset[0]["lead_source"] == "apollo_people"
    assert dataset[0]["email_quality_score"] == 95
    assert "apollo_match" in dataset[0]["lead_capture_reason"]
    assert dataset[0]["lead_relevance_score"] == 197
    assert dataset[0]["lead_count"] == 2
    assert dataset[0]["apollo_leads_count"] == 1
    assert dataset[0]["hunter_leads_count"] == 1
    assert dataset[0]["contacts_with_email_count"] == 1
    assert dataset[0]["contacts_with_linkedin_count"] == 2
    assert Path(ctx.paths["opportunities_export"]).exists()
    assert Path(ctx.paths["top_opportunities_export"]).exists()

    with open(ctx.paths["opportunities_export"], newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames is not None
        assert "company_key" in reader.fieldnames
        assert "opportunity_score" in reader.fieldnames
        assert "lead_confidence" in reader.fieldnames
        assert "email_quality_score" in reader.fieldnames
        assert "lead_capture_reason" in reader.fieldnames
        assert "lead_relevance_score" in reader.fieldnames
        assert "lead_count" in reader.fieldnames
        assert "apollo_leads_count" in reader.fieldnames
        assert "hunter_leads_count" in reader.fieldnames
        assert "contacts_with_email_count" in reader.fieldnames
        assert "contacts_with_linkedin_count" in reader.fieldnames
