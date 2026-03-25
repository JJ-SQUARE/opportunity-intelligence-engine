from oie.orchestration.run_context import RunContext
from oie.services.company_identity_service import CompanyIdentityService


def test_same_root_does_not_merge_unrelated_brands():
    ctx = RunContext.create(config={})
    svc = CompanyIdentityService(ctx)

    left = {
        "company_key": "cmp_sofka",
        "company_display": "Sofka Technologies",
        "company_normalized": "sofka technologies",
        "resolved_domain": None,
    }
    right = {
        "company_key": "cmp_quid",
        "company_display": "Quid Solutions",
        "company_normalized": "quid solutions",
        "resolved_domain": None,
    }

    assert svc._is_safe_same_root_merge(left, right) is False


def test_same_root_allows_exact_or_contained_brand_match():
    ctx = RunContext.create(config={})
    svc = CompanyIdentityService(ctx)

    left = {
        "company_key": "cmp_sofka_1",
        "company_display": "Sofka",
        "company_normalized": "sofka",
        "resolved_domain": None,
    }
    right = {
        "company_key": "cmp_sofka_2",
        "company_display": "Sofka Technologies",
        "company_normalized": "sofka technologies",
        "resolved_domain": None,
    }

    assert svc._is_safe_same_root_merge(left, right) is True


def test_same_root_allows_shared_resolved_domain():
    ctx = RunContext.create(config={})
    svc = CompanyIdentityService(ctx)

    left = {
        "company_key": "cmp_1",
        "company_display": "Michael Page",
        "company_normalized": "michael page",
        "resolved_domain": "michaelpage.com",
    }
    right = {
        "company_key": "cmp_2",
        "company_display": "Michael Page Colombia",
        "company_normalized": "michael page colombia",
        "resolved_domain": "michaelpage.com",
    }

    assert svc._is_safe_same_root_merge(left, right) is True
