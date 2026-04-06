from oie.orchestration.run_context import RunContext
from oie.services.job_dedup_service import JobDedupService


def test_job_dedup_service_dedupes_and_sets_metrics():
    ctx = RunContext.create(config={}, flags={})
    service = JobDedupService(ctx)

    jobs = [
        {
            "company": "Acme",
            "job_title": "Backend Engineer",
            "location": "Remote",
            "url": "https://acme.com/jobs/1",
        },
        {
            "company": "Acme",
            "job_title": "Backend Engineer",
            "location": "Remote",
            "url": "https://acme.com/jobs/1",
        },
        {
            "company": "Beta",
            "job_title": "Data Engineer",
            "location": "Remote",
            "url": "https://beta.com/jobs/2",
        },
    ]

    result = service.dedupe(jobs)

    assert len(result) == 2
    assert ctx.metrics["jobs_before_dedupe"] == 3
    assert ctx.metrics["jobs_after_dedupe"] == 2
    assert ctx.metrics["jobs_deduplicated"] == 1
    assert ctx.metrics["dedupe_completed"] is True


def test_job_dedup_service_respects_real_fingerprint_fields():
    ctx = RunContext.create(config={}, flags={})
    service = JobDedupService(ctx)

    jobs = [
        {
            "title": "Backend Engineer I",
            "company": "Acme",
            "job_title": "Backend Engineer",
            "location": "Remote",
            "url": "https://acme.com/jobs/1",
        },
        {
            "title": "Backend Engineer II",
            "company": "Acme",
            "job_title": "Backend Engineer",
            "location": "Remote",
            "url": "https://acme.com/jobs/1",
        },
    ]

    result = service.dedupe(jobs)

    assert len(result) == 1
    assert result[0]["title"] == "Backend Engineer I"
    assert ctx.metrics["jobs_before_dedupe"] == 2
    assert ctx.metrics["jobs_after_dedupe"] == 1
    assert ctx.metrics["jobs_deduplicated"] == 1
