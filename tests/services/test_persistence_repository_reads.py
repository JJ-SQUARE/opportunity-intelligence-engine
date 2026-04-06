from oie.orchestration.run_context import RunContext
from oie.persistence.repositories import (
    CompanyRepository,
    JobRepository,
    LeadRepository,
    ProviderEventRepository,
    RunMetricsRepository,
    RunRepository,
)
from oie.services.persistence_service import PersistenceService


def test_repository_read_helpers_return_persisted_data(tmp_path):
    db_path = tmp_path / "oie_repo_reads.db"

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    ctx.metrics["jobs_after_dedupe"] = 2
    ctx.metrics["custom_flag"] = "ok"
    ctx.add_provider_event(
        provider="openai",
        event_type="execution_error",
        message="boom",
        metadata={"status_code": 500, "detail": "x"},
    )

    PersistenceService(ctx).persist_run_snapshot(
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
                "detected_at": "2026-03-10",
            }
        ],
        leads=[
            {
                "company_key": "cmp_a",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "jane@acme.com",
                "linkedin_url": "https://linkedin.com/in/jane",
                "lead_source": "apollo_people",
                "lead_confidence": 0.9,
            }
        ],
    )

    run_row = RunRepository(str(db_path)).get_run(ctx.run_id)
    assert run_row is not None
    assert run_row["status"] == "ok"

    metrics = RunMetricsRepository(str(db_path)).get_metrics(ctx.run_id)
    assert metrics["jobs_after_dedupe"] == "2"
    assert metrics["custom_flag"] == "ok"

    events = ProviderEventRepository(str(db_path)).list_by_run(ctx.run_id)
    assert len(events) == 1
    assert events[0]["provider"] == "openai"
    assert events[0]["metadata"]["detail"] == "x"

    companies = CompanyRepository(str(db_path)).list_companies()
    assert len(companies) == 1
    assert companies[0]["company_key"] == "cmp_a"

    jobs = JobRepository(str(db_path)).list_jobs_by_run(ctx.run_id)
    assert len(jobs) == 1
    assert jobs[0]["company_key"] == "cmp_a"

    leads = LeadRepository(str(db_path)).list_leads_by_run(ctx.run_id)
    assert len(leads) == 1
    assert leads[0]["email"] == "jane@acme.com"
