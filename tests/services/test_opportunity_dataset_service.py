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
    assert Path(ctx.paths["opportunities_export"]).exists()
    assert Path(ctx.paths["top_opportunities_export"]).exists()
