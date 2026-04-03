from oie.orchestration.run_context import RunContext
from oie.services.hiring_signals_service import HiringSignalsService


def test_hiring_signals_service_aggregates_remote_and_contractor_signals():
    ctx = RunContext.create(config={}, flags={})
    service = HiringSignalsService(ctx)

    jobs = [
        {
            "company": "Acme",
            "source": "google_jobs",
            "is_remote": True,
            "is_contractor": False,
            "apply_url": "https://acme.com/apply/1",
            "job_url": "https://acme.com/jobs/1",
        },
        {
            "company": "Acme",
            "source": "linkedin_serpapi",
            "is_remote": False,
            "is_contractor": True,
            "url": "https://acme.com/careers",
        },
    ]

    companies = service.aggregate_by_company(jobs)

    assert len(companies) == 1
    company = companies[0]

    assert company["company"] == "Acme"
    assert company["total_openings"] == 2
    assert company["remote_jobs"] == 1
    assert company["contractor_jobs"] == 1
    assert company["remote_friendly"] is True
    assert company["contractor_signal"] is True
    assert company["multi_source_signal"] is True
    assert company["apply_url"] == "https://acme.com/apply/1"
    assert company["job_url"] == "https://acme.com/jobs/1"
    assert company["url"] == "https://acme.com/careers"
    assert ctx.metrics["companies_detected"] == 1
    assert ctx.metrics["signals_completed"] is True


def test_hiring_signals_service_supports_legacy_flag_names():
    ctx = RunContext.create(config={}, flags={})
    service = HiringSignalsService(ctx)

    jobs = [
        {
            "company": "Beta",
            "source": "google_jobs",
            "remote_flag": True,
            "contractor_flag": True,
        }
    ]

    companies = service.aggregate_by_company(jobs)

    assert len(companies) == 1
    company = companies[0]
    assert company["remote_jobs"] == 1
    assert company["contractor_jobs"] == 1
