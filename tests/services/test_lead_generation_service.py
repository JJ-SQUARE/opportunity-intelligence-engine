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
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 25,
            }
        ]
    )

    assert len(leads) == 1
    assert leads[0]["lead_source"] == "apollo_people"
    assert leads[0]["email"] == "jane@acme.com"
    assert leads[0]["company_display"] == ""
    assert leads[0]["resolved_domain"] == "acme.com"
    assert leads[0]["company_type_ai"] == "end_client"
    assert leads[0]["opportunity_score"] == 25
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
                    "value": "john.smith@acme.com",
                    "position": "VP Engineering",
                    "first_name": "John",
                    "last_name": "Smith",
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
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 25,
            }
        ]
    )

    assert len(leads) == 1
    assert leads[0]["lead_source"] == "hunter_domain_search"
    assert leads[0]["email"] == "john.smith@acme.com"


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


def test_lead_generation_service_filters_generic_hunter_emails(tmp_path):
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
                {"value": "jobs@beta.com", "position": "", "first_name": "", "last_name": ""},
                {"value": "hello@beta.com", "position": "", "first_name": "", "last_name": ""},
                {
                    "value": "brian.mcgovern@beta.com",
                    "position": "",
                    "first_name": "Brian",
                    "last_name": "McGovern",
                    "linkedin": "",
                },
            ]
        }
    }

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_beta",
                "resolved_domain": "beta.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 22,
            }
        ]
    )

    assert len(leads) == 1
    assert leads[0]["email"] == "brian.mcgovern@beta.com"
    assert ctx.metrics["hunter_leads_filtered_generic_email"] >= 2


def test_lead_generation_service_limits_hunter_results_per_company(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
            "lead_generation": {"max_hunter_results_per_company": 2},
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
                    "value": "alice.smith@beta.com",
                    "position": "VP Engineering",
                    "first_name": "Alice",
                    "last_name": "Smith",
                },
                {
                    "value": "bob.jones@beta.com",
                    "position": "Engineering Director",
                    "first_name": "Bob",
                    "last_name": "Jones",
                },
                {
                    "value": "carol.lee@beta.com",
                    "position": "",
                    "first_name": "Carol",
                    "last_name": "Lee",
                },
            ]
        }
    }

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_beta",
                "resolved_domain": "beta.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 22,
            }
        ]
    )

    assert len(leads) == 2
    emails = {lead["email"] for lead in leads}
    assert "alice.smith@beta.com" in emails
    assert "bob.jones@beta.com" in emails

def test_lead_generation_service_apollo_sets_quality_and_reason(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
            "providers": {
                "limits": {"apollo": 5, "hunter": 5},
                "clients": {
                    "apollo": {"api_key": "fake-apollo"},
                    "hunter": {"api_key": "fake-hunter"},
                },
            },
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
                "first_name": "Jane",
                "last_name": "Doe",
                "title": "CTO",
                "email": "jane.doe@acme.com",
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
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 25,
            }
        ]
    )

    assert len(leads) == 1
    assert leads[0]["lead_source"] == "apollo_people"
    assert leads[0]["email_quality_score"] > 0
    assert "apollo_match" in leads[0]["lead_capture_reason"]
    assert "title:CTO" in leads[0]["lead_capture_reason"]
    assert "email_quality:" in leads[0]["lead_capture_reason"]

def test_lead_generation_service_hunter_sets_quality_reason_and_confidence(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
            "providers": {
                "limits": {"apollo": 5, "hunter": 5},
                "clients": {
                    "apollo": {"api_key": "fake-apollo"},
                    "hunter": {"api_key": "fake-hunter"},
                },
            },
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
                    "value": "john.smith@acme.com",
                    "position": "VP Engineering",
                    "first_name": "John",
                    "last_name": "Smith",
                    "linkedin": "https://linkedin.com/in/johnsmith",
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
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 25,
            }
        ]
    )

    assert len(leads) == 1
    assert leads[0]["lead_source"] == "hunter_domain_search"
    assert leads[0]["email_quality_score"] >= 40
    assert "hunter_match" in leads[0]["lead_capture_reason"]
    assert "title:VP Engineering" in leads[0]["lead_capture_reason"]
    assert 0.45 <= leads[0]["lead_confidence"] <= 0.85


def test_lead_generation_service_supplements_weak_apollo_with_hunter(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
            "lead_generation": {
                "max_leads_per_company": 3,
                "max_hunter_results_per_company": 2,
                "max_apollo_results_per_company": 2,
            },
            "providers": {
                "limits": {"apollo": 5, "hunter": 5},
                "clients": {
                    "apollo": {"api_key": "fake-apollo"},
                    "hunter": {"api_key": "fake-hunter"},
                },
            },
        },
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    calls = {"apollo": 0, "hunter": 0}

    apollo_client = control.registry.get_client("apollo")
    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {
            "people": [
                {
                    "name": "Chris Weak",
                    "first_name": "Chris",
                    "last_name": "Weak",
                    "title": "Head of Engineering",
                    "email": "",
                    "linkedin_url": "",
                }
            ]
        }
    apollo_client.search_people_by_domain_and_titles = fake_apollo

    hunter_client = control.registry.get_client("hunter")
    def fake_hunter(domain):
        calls["hunter"] += 1
        return {
            "data": {
                "emails": [
                    {
                        "value": "jane.strong@acme.com",
                        "position": "VP Engineering",
                        "first_name": "Jane",
                        "last_name": "Strong",
                        "linkedin": "https://linkedin.com/in/janestrong",
                    }
                ]
            }
        }
    hunter_client.search_domain_contacts = fake_hunter

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_acme",
                "resolved_domain": "acme.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 25,
                "industry": "software",
                "enrichment_source": "apollo",
            }
        ]
    )

    assert calls["apollo"] == 1
    assert calls["hunter"] == 1
    assert len(leads) == 2
    assert leads[0]["lead_source"] == "hunter_domain_search"
    assert leads[0]["email"] == "jane.strong@acme.com"
    assert {lead["lead_source"] for lead in leads} == {"apollo_people", "hunter_domain_search"}

def test_is_relevant_title_accepts_founder_with_technical_scope(tmp_path):
    ctx = RunContext.create(
        config={"cache": {"base_dir": str(tmp_path / "http_cache")}, "providers": {"limits": {}, "clients": {}}},
        flags={},
    )
    control = ProviderControlService(ctx)
    service = LeadGenerationService(ctx, control)

    assert service._is_relevant_title("Founder & CTO") is True
    assert service._is_relevant_title("CEO / Head of Technology") is True


def test_is_relevant_title_rejects_senior_non_technical_titles(tmp_path):
    ctx = RunContext.create(
        config={"cache": {"base_dir": str(tmp_path / "http_cache")}, "providers": {"limits": {}, "clients": {}}},
        flags={},
    )
    control = ProviderControlService(ctx)
    service = LeadGenerationService(ctx, control)

    assert service._is_relevant_title("VP Sales") is False
    assert service._is_relevant_title("Director of Marketing") is False
    assert service._is_relevant_title("Chief People Officer") is False


def test_is_relevant_title_rejects_technical_but_low_signal_individual_titles(tmp_path):
    ctx = RunContext.create(
        config={"cache": {"base_dir": str(tmp_path / "http_cache")}, "providers": {"limits": {}, "clients": {}}},
        flags={},
    )
    control = ProviderControlService(ctx)
    service = LeadGenerationService(ctx, control)

    assert service._is_relevant_title("Junior Software Developer") is False
    assert service._is_relevant_title("Support Engineer") is False
    assert service._is_relevant_title("QA Analyst") is False


def test_is_relevant_title_accepts_common_buyer_titles(tmp_path):
    ctx = RunContext.create(
        config={"cache": {"base_dir": str(tmp_path / "http_cache")}, "providers": {"limits": {}, "clients": {}}},
        flags={},
    )
    control = ProviderControlService(ctx)
    service = LeadGenerationService(ctx, control)

    assert service._is_relevant_title("VP of Engineering") is True
    assert service._is_relevant_title("Director of Software Engineering") is True
    assert service._is_relevant_title("Head of Platform Engineering") is True
    assert service._is_relevant_title("IT Director") is True


def test_lead_generation_service_skips_competitor_company(tmp_path):
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
    hunter_client = control.registry.get_client("hunter")
    calls = {"apollo": 0, "hunter": 0}

    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {"people": []}

    def fake_hunter(domain):
        calls["hunter"] += 1
        return {"data": {"emails": []}}

    apollo_client.search_people_by_domain_and_titles = fake_apollo
    hunter_client.search_domain_contacts = fake_hunter

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_competitor",
                "resolved_domain": "competitor.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "competitor",
                "classification_confidence_ai": 1.0,
                "opportunity_score": 60,
                "benchmark_only": True,
            }
        ]
    )

    assert leads == []
    assert calls["apollo"] == 0
    assert calls["hunter"] == 0

def test_lead_generation_service_allows_accepted_domain_without_full_enrichment(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
            "lead_generation": {"max_companies_per_run": 5},
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

    calls = {"apollo": 0}

    apollo_client = control.registry.get_client("apollo")
    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {
            "people": [
                {
                    "name": "Jane Domain",
                    "title": "CTO",
                    "email": "jane@signalco.com",
                    "linkedin_url": "https://linkedin.com/in/janedomain",
                }
            ]
        }
    apollo_client.search_people_by_domain_and_titles = fake_apollo

    hunter_client = control.registry.get_client("hunter")
    hunter_client.search_domain_contacts = lambda domain: {"data": {"emails": []}}

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_signal_only",
                "resolved_domain": "signalco.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "unknown",
                "classification_confidence_ai": 0.2,
                "opportunity_score": 26,
            },
            {
                "company_key": "cmp_enriched",
                "resolved_domain": "enrichedco.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 24,
                "industry": "software",
                "linkedin_company_url": "https://linkedin.com/company/enrichedco",
            },
        ]
    )

    assert len(leads) >= 1
    assert any(lead["company_key"] == "cmp_signal_only" for lead in leads)
    assert calls["apollo"] >= 1
    assert ctx.metrics["lead_generation_require_enrichment"] is False
    assert ctx.metrics["lead_generation_skipped_missing_enrichment"] == 0


def test_lead_generation_service_skips_high_confidence_outsourcing_company(tmp_path):
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
    hunter_client = control.registry.get_client("hunter")
    calls = {"apollo": 0, "hunter": 0}

    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {"people": []}

    def fake_hunter(domain):
        calls["hunter"] += 1
        return {"data": {"emails": []}}

    apollo_client.search_people_by_domain_and_titles = fake_apollo
    hunter_client.search_domain_contacts = fake_hunter

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_outsourcing",
                "resolved_domain": "vendorco.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "outsourcing",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 55,
                "industry": "Information Technology and Services",
            }
        ]
    )

    assert leads == []
    assert calls["apollo"] == 0
    assert calls["hunter"] == 0

def test_lead_generation_service_skips_consulting_company_even_with_accepted_domain(tmp_path):
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
    hunter_client = control.registry.get_client("hunter")
    calls = {"apollo": 0, "hunter": 0}

    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {"people": []}

    def fake_hunter(domain):
        calls["hunter"] += 1
        return {"data": {"emails": []}}

    apollo_client.search_people_by_domain_and_titles = fake_apollo
    hunter_client.search_domain_contacts = fake_hunter

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_consulting",
                "resolved_domain": "consultingco.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "consulting",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 70,
            }
        ]
    )

    assert leads == []
    assert calls["apollo"] == 0
    assert calls["hunter"] == 0


def test_lead_generation_service_unknown_with_low_score_is_filtered_out(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
            "lead_generation": {"min_opportunity_score": 15},
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
    hunter_client = control.registry.get_client("hunter")
    calls = {"apollo": 0, "hunter": 0}

    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {"people": []}

    def fake_hunter(domain):
        calls["hunter"] += 1
        return {"data": {"emails": []}}

    apollo_client.search_people_by_domain_and_titles = fake_apollo
    hunter_client.search_domain_contacts = fake_hunter

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_unknown_low",
                "resolved_domain": "unknownlow.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "unknown",
                "classification_confidence_ai": 0.1,
                "opportunity_score": 12,
            }
        ]
    )

    assert leads == []
    assert calls["apollo"] == 0
    assert calls["hunter"] == 0



def test_lead_generation_service_normalizes_staffing_agency_and_skips_it(tmp_path):
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
    hunter_client = control.registry.get_client("hunter")
    calls = {"apollo": 0, "hunter": 0}

    def fake_apollo(domain, titles):
        calls["apollo"] += 1
        return {"people": []}

    def fake_hunter(domain):
        calls["hunter"] += 1
        return {"data": {"emails": []}}

    apollo_client.search_people_by_domain_and_titles = fake_apollo
    hunter_client.search_domain_contacts = fake_hunter

    service = LeadGenerationService(ctx, control)
    leads = service.generate_leads(
        [
            {
                "company_key": "cmp_staffing_alias",
                "resolved_domain": "staffingco.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "staffing_agency",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 70,
            }
        ]
    )

    assert leads == []
    assert calls["apollo"] == 0
    assert calls["hunter"] == 0

def test_lead_generation_service_skips_rejected_domain_even_without_require_accepted_domain(tmp_path):
    ctx = RunContext.create(
        config={
            "cache": {"base_dir": str(tmp_path / "http_cache")},
            "lead_generation": {"require_accepted_domain": False},
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
                "company_key": "cmp_rejected",
                "resolved_domain": "rejectedco.com",
                "domain_validation_status": "rejected",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.9,
                "opportunity_score": 30,
            }
        ]
    )

    assert leads == []
    assert calls["apollo"] == 0

