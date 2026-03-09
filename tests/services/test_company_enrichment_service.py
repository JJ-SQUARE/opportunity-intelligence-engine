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
