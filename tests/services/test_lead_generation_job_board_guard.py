from oie.orchestration.run_context import RunContext
from oie.services.lead_generation_service import LeadGenerationService
from oie.services.provider_control_service import ProviderControlService


def test_stub_lead_not_generated_for_job_board_domain():
    ctx = RunContext.create(config={}, flags={})
    provider_control = ProviderControlService(ctx)
    service = LeadGenerationService(ctx, provider_control)

    companies = [
        {
            "company_key": "cmp_1",
            "resolved_domain": "mx.jooble.org",
        }
    ]

    leads = service.generate_leads(companies)
    assert leads == []
