from oie.orchestration.run_context import RunContext
from oie.services.lead_generation_service import LeadGenerationService
from oie.services.provider_control_service import ProviderControlService


def test_lead_generation_service_uses_apollo_people_search():
    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"apollo": 5, "hunter": 5},
                "clients": {
                    "apollo": {"api_key": "fake-apollo"},
                    "hunter": {"api_key": "fake-hunter"},
                },
            }
        },
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    apollo_client = control.registry.get_client("apollo")
    apollo_client.search_people_by_domain_and_titles = lambda domain, titles: {
        "people": [
            {
                "name": "Jane Doe",
                "title": "CTO",
                "email": "jane@acme.com",
                "linkedin_url": "https://linkedin.com/in/janedoe",
            }
        ]
    }

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_acme",
                "resolved_domain": "acme.com",
            }
        ]
    )

    assert len(leads) == 1
    assert leads[0]["lead_source"] == "apollo_people"
    assert leads[0]["email"] == "jane@acme.com"
    assert ctx.metrics["leads_generated"] == 1


def test_lead_generation_service_falls_back_to_hunter():
    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"apollo": 5, "hunter": 5},
                "clients": {
                    "apollo": {"api_key": "fake-apollo"},
                    "hunter": {"api_key": "fake-hunter"},
                },
            }
        },
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    apollo_client = control.registry.get_client("apollo")
    apollo_client.search_people_by_domain_and_titles = lambda domain, titles: {"people": []}

    hunter_client = control.registry.get_client("hunter")
    hunter_client.search_domain_contacts = lambda domain: {
        "data": {
            "emails": [
                {
                    "value": "vp@acme.com",
                    "position": "VP Engineering",
                    "first_name": "John",
                    "linkedin": "https://linkedin.com/in/john",
                }
            ]
        }
    }

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_acme",
                "resolved_domain": "acme.com",
            }
        ]
    )

    assert len(leads) == 1
    assert leads[0]["lead_source"] == "hunter_domain_search"
    assert leads[0]["email"] == "vp@acme.com"


def test_lead_generation_service_respects_no_enrichment():
    ctx = RunContext.create(config={}, flags={"no_enrichment": True})
    control = ProviderControlService(ctx)
    control.initialize()

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads([{"company_key": "cmp_acme"}])

    assert leads == []
    assert ctx.metrics["lead_generation_skipped_no_enrichment"] is True
