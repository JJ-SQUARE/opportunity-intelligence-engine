from oie.orchestration.run_context import RunContext
from oie.services.company_identity_service import CompanyIdentityService


def test_strong_brand_match_positive():
    ctx = RunContext.create(config={})
    svc = CompanyIdentityService(ctx)

    left = {
        "company_normalized": "sofka",
        "resolved_domain": None,
    }
    right = {
        "company_normalized": "sofka technologies",
        "resolved_domain": None,
    }

    assert svc._is_strong_brand_match(left, right) is True


def test_strong_brand_match_negative():
    ctx = RunContext.create(config={})
    svc = CompanyIdentityService(ctx)

    left = {
        "company_normalized": "sofka technologies",
        "resolved_domain": None,
    }
    right = {
        "company_normalized": "quid solutions",
        "resolved_domain": None,
    }

    assert svc._is_strong_brand_match(left, right) is False


def test_strong_brand_respects_domain_conflict():
    ctx = RunContext.create(config={})
    svc = CompanyIdentityService(ctx)

    left = {
        "company_normalized": "sofka",
        "resolved_domain": "sofka.com",
    }
    right = {
        "company_normalized": "sofka technologies",
        "resolved_domain": "other.com",
    }

    assert svc._is_strong_brand_match(left, right) is False
