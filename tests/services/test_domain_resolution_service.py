from oie.orchestration.run_context import RunContext
from oie.services.domain_resolution_service import DomainResolutionService


def test_extract_valid_domain():
    ctx = RunContext.create(config={})
    service = DomainResolutionService(ctx)

    domain = service._extract_domain("https://www.acme.com/careers/job-1")

    assert domain == "acme.com"


def test_blocked_domain_is_rejected():
    ctx = RunContext.create(config={})
    service = DomainResolutionService(ctx)

    companies = [
        {
            "company": "Example",
            "apply_url": "https://boards.greenhouse.io/example/jobs/123",
            "job_url": None,
            "url": None,
        }
    ]

    resolved = service.resolve_domains(companies)

    assert resolved[0]["resolved_domain"] is None


def test_apply_url_priority_for_resolution():
    ctx = RunContext.create(config={})
    service = DomainResolutionService(ctx)

    companies = [
        {
            "company": "Example",
            "apply_url": "https://acme.com/apply/123",
            "job_url": "https://linkedin.com/jobs/view/123",
            "url": None,
        }
    ]

    resolved = service.resolve_domains(companies)

    assert resolved[0]["resolved_domain"] == "acme.com"
    assert resolved[0]["domain_source"] == "apply_url"
