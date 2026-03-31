from oie.orchestration.run_context import RunContext
from oie.services.domain_resolution_service import DomainResolutionService


def test_priority_zero_for_aggregator_with_extracted_actionable_name():
    ctx = RunContext.create(config={})
    service = DomainResolutionService(ctx, provider_control_service=None)

    company = {
        "company_display": "Confidencial",
        "title": "Backend Engineer at Tenaris",
        "snippet": "Remote role",
        "apply_url": "https://jobgether.com/offer/123",
        "url": None,
    }

    assert service._classify_resolution_priority(company) == 0


def test_priority_three_for_confidential_without_actionable_name():
    ctx = RunContext.create(config={})
    service = DomainResolutionService(ctx, provider_control_service=None)

    company = {
        "company_display": "Confidencial",
        "title": "Backend Engineer",
        "snippet": "Great opportunity",
        "apply_url": "https://jobgether.com/offer/123",
        "url": None,
    }

    assert service._classify_resolution_priority(company) == 3


def test_priority_one_for_actionable_name_without_direct_urls():
    ctx = RunContext.create(config={})
    service = DomainResolutionService(ctx, provider_control_service=None)

    company = {
        "company_display": "Tenaris",
        "title": None,
        "snippet": None,
        "apply_url": None,
        "url": None,
    }

    assert service._classify_resolution_priority(company) == 1
