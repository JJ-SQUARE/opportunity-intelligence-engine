from oie.orchestration.run_context import RunContext
from oie.services.lead_generation_service import LeadGenerationService


def test_lead_generation_service_generates_stub_leads():
    ctx = RunContext.create(config={}, flags={})
    service = LeadGenerationService(ctx)

    companies = [
        {
            "company_key": "cmp_acme",
            "company_display": "Acme Inc.",
            "resolved_domain": "acme.com",
        }
    ]

    leads = service.generate_leads(companies)

    assert len(leads) == 1
    assert leads[0]["company_key"] == "cmp_acme"
    assert leads[0]["email"] == "engineering@acme.com"
    assert ctx.metrics["leads_generated"] == 1


def test_lead_generation_service_respects_no_enrichment():
    ctx = RunContext.create(config={}, flags={"no_enrichment": True})
    service = LeadGenerationService(ctx)

    leads = service.generate_leads([{"company_key": "cmp_acme"}])

    assert leads == []
    assert ctx.metrics["lead_generation_skipped_no_enrichment"] is True
