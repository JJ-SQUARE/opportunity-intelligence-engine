from oie.orchestration.run_context import RunContext
from oie.services.lead_generation_service import LeadGenerationService
from oie.services.provider_control_service import ProviderControlService


def test_lead_generation_service_uses_apollo_people_search(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
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


def test_lead_generation_service_falls_back_to_hunter(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
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


def test_lead_generation_service_respects_no_enrichment(tmp_path):
    ctx = RunContext.create(
        config={"cache": {"base_dir": str(tmp_path / "http_cache")}},
        flags={"no_enrichment": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads([{"company_key": "cmp_acme"}])

    assert leads == []
    assert ctx.metrics["lead_generation_skipped_no_enrichment"] is True

def test_lead_generation_service_skips_review_company(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
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
    calls = {"apollo": 0}

    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {"people": []}

    apollo_client.search_people_by_domain_and_titles = fake_apollo

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_review",
                "resolved_domain": "reviewco.com",
                "domain_validation_status": "review",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.9,
                "opportunity_score": 20,
            }
        ]
    )

    assert leads == []
    assert calls["apollo"] == 0
    assert ctx.metrics["leads_generated"] == 0


def test_lead_generation_service_skips_job_board_domain(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
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
    calls = {"apollo": 0}

    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {"people": []}

    apollo_client.search_people_by_domain_and_titles = fake_apollo

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_jobgether",
                "resolved_domain": "jobgether.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.9,
                "opportunity_score": 20,
            }
        ]
    )

    assert leads == []
    assert calls["apollo"] == 0
    assert ctx.metrics["leads_generated"] == 0


def test_lead_generation_service_does_not_retry_failed_apollo_domain_in_same_run(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
            "providers": {
                "limits": {"apollo": 5, "hunter": 5},
                "retry_policy": {
                    "apollo": {
                        "max_attempts": 1
                    }
                },
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
    calls = {"apollo": 0}

    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        raise ValueError("boom")

    apollo_client.search_people_by_domain_and_titles = fake_apollo

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_a",
                "resolved_domain": "acme.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.9,
                "opportunity_score": 20,
            },
            {
                "company_key": "cmp_b",
                "resolved_domain": "acme.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.9,
                "opportunity_score": 20,
            },
        ]
    )

    assert leads == []
    assert calls["apollo"] == 1
    assert "acme.com" in service._failed_apollo_lead_domains


def test_lead_generation_service_skips_non_end_client_when_confident(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
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
    calls = {"apollo": 0}

    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {"people": []}

    apollo_client.search_people_by_domain_and_titles = fake_apollo

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_vendor",
                "resolved_domain": "vendor.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "staffing",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 20,
            }
        ]
    )

    assert leads == []
    assert calls["apollo"] == 0

