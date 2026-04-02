from types import SimpleNamespace
from oie.orchestration.run_context import RunContext
from oie.services.company_enrichment_service import CompanyEnrichmentService
from oie.services.provider_control_service import ProviderControlService


def test_company_enrichment_service_enriches_company_with_apollo_stub():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30
            }
        },
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    client = control.registry.get_client("apollo")
    client.enrich_company_by_domain = lambda domain: {
        "organization": {
            "industry": "Software",
            "estimated_num_employees": "51-200",
            "linkedin_url": "https://linkedin.com/company/acme",
            "short_description": "Builds software",
        }
    }

    service = CompanyEnrichmentService(ctx, control)

    companies = [
        {
            "company_key": "cmp_acme",
            "company_display": "Acme Inc.",
            "resolved_domain": "acme.com",
        }
    ]

    enriched = service.enrich_companies(companies)

    assert enriched[0]["industry"] == "Software"
    assert enriched[0]["employee_range"] == "51-200"
    assert enriched[0]["linkedin_company_url"] == "https://linkedin.com/company/acme"
    assert enriched[0]["enrichment_source"] == "apollo"
    assert ctx.metrics["companies_enriched"] == 1


def test_company_enrichment_service_respects_no_enrichment_flag():
    ctx = RunContext.create(config={}, flags={"no_enrichment": True})
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyEnrichmentService(ctx, control)
    companies = [{"company_key": "cmp_acme", "resolved_domain": "acme.com"}]

    result = service.enrich_companies(companies)

    assert result == companies
    assert ctx.metrics["company_enrichment_skipped_no_enrichment"] is True

def test_company_enrichment_service_skips_review_domain():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30
            }
        },
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    client = control.registry.get_client("apollo")
    calls = {"n": 0}

    def fake_enrich(domain):
        calls["n"] += 1
        return {"organization": {"industry": "Software"}}

    client.enrich_company_by_domain = fake_enrich

    service = CompanyEnrichmentService(ctx, control)

    companies = [
        {
            "company_key": "cmp_review",
            "company_display": "Review Co",
            "resolved_domain": "reviewco.com",
            "domain_validation_status": "review",
        }
    ]

    enriched = service.enrich_companies(companies)

    assert calls["n"] == 0
    assert enriched[0].get("industry") in (None, "")
    assert ctx.metrics["companies_enriched"] == 0


def test_company_enrichment_service_skips_job_board_domain():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30
            }
        },
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    client = control.registry.get_client("apollo")
    calls = {"n": 0}

    def fake_enrich(domain):
        calls["n"] += 1
        return {"organization": {"industry": "Software"}}

    client.enrich_company_by_domain = fake_enrich

    service = CompanyEnrichmentService(ctx, control)

    companies = [
        {
            "company_key": "cmp_jobgether",
            "company_display": "Jobgether Listing",
            "resolved_domain": "jobgether.com",
            "domain_validation_status": "accepted",
        }
    ]

    enriched = service.enrich_companies(companies)

    assert calls["n"] == 0
    assert enriched[0].get("industry") in (None, "")
    assert ctx.metrics["companies_enriched"] == 0


def test_company_enrichment_service_does_not_retry_failed_domain_in_same_run():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "retry_policy": {
                    "apollo": {
                        "max_attempts": 1
                    }
                },
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30
            }
        },
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    client = control.registry.get_client("apollo")
    calls = {"n": 0}

    def fake_enrich(domain):
        calls["n"] += 1
        raise ValueError("boom")

    client.enrich_company_by_domain = fake_enrich

    service = CompanyEnrichmentService(ctx, control)

    companies = [
        {
            "company_key": "cmp_a",
            "company_display": "Acme A",
            "resolved_domain": "same-run-fail-example.com",
            "domain_validation_status": "accepted",
        },
        {
            "company_key": "cmp_b",
            "company_display": "Acme B",
            "resolved_domain": "same-run-fail-example.com",
            "domain_validation_status": "accepted",
        },
    ]

    enriched = service.enrich_companies(companies)

    assert len(enriched) == 2
    assert calls["n"] == 1
    assert "same-run-fail-example.com" in service._failed_enrichment_domains
    assert ctx.metrics["companies_enriched"] == 0

