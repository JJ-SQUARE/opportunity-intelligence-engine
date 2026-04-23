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
            "company_display": "Same Run Fail Example",
            "resolved_domain": "same-run-fail-example.com",
            "domain_validation_status": "accepted",
        },
        {
            "company_key": "cmp_b",
            "company_display": "Same Run Fail Example",
            "resolved_domain": "same-run-fail-example.com",
            "domain_validation_status": "accepted",
        },
    ]

    enriched = service.enrich_companies(companies)

    assert len(enriched) == 2
    assert calls["n"] == 1
    assert "same-run-fail-example.com" in service._failed_enrichment_domains
    assert ctx.metrics["companies_enriched"] == 0

def test_company_enrichment_service_skips_low_opportunity_score():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30,
                "min_opportunity_score": 15,
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
            "company_key": "cmp_low",
            "company_display": "Low Score Co",
            "resolved_domain": "lowscore.com",
            "domain_validation_status": "accepted",
            "company_type_ai": "end_client",
            "classification_confidence_ai": 0.95,
            "opportunity_score": 10,
        }
    ]

    enriched = service.enrich_companies(companies)

    assert calls["n"] == 0
    assert enriched[0].get("industry") in (None, "")
    assert ctx.metrics["company_enrichment_candidates_total"] == 0
    assert ctx.metrics["company_enrichment_selected_total"] == 0
    assert ctx.metrics["company_enrichment_skipped_limit"] == 0
    assert ctx.metrics["companies_enriched"] == 0


def test_company_enrichment_service_skips_disallowed_company_type_with_high_confidence():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30,
                "allowed_company_types": ["end_client"],
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
            "company_key": "cmp_consulting",
            "company_display": "Consulting Co",
            "resolved_domain": "consultingco.com",
            "domain_validation_status": "accepted",
            "company_type_ai": "consulting",
            "classification_confidence_ai": 0.95,
            "opportunity_score": 30,
        }
    ]

    enriched = service.enrich_companies(companies)

    assert calls["n"] == 0
    assert enriched[0].get("industry") in (None, "")
    assert ctx.metrics["company_enrichment_candidates_total"] == 0
    assert ctx.metrics["company_enrichment_selected_total"] == 0
    assert ctx.metrics["company_enrichment_skipped_limit"] == 0
    assert ctx.metrics["companies_enriched"] == 0


def test_company_enrichment_service_skips_non_actionable_company_name_even_with_domain():
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

    enriched = service.enrich_companies(
        [
            {
                "company_key": "cmp_conf",
                "company_display": "Empresa Confidencial",
                "resolved_domain": "empresaconfidencial.com",
                "domain_validation_status": "accepted",
                "opportunity_score": 30,
            }
        ]
    )

    assert calls["n"] == 0
    assert enriched[0].get("industry") in (None, "")
    assert ctx.metrics["company_enrichment_candidates_total"] == 0


def test_company_enrichment_service_skips_weak_company_domain_match():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30,
                "min_domain_match_confidence": 0.80,
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

    enriched = service.enrich_companies(
        [
            {
                "company_key": "cmp_mismatch",
                "company_display": "NOUS",
                "resolved_domain": "securitycameras.example.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "unknown",
                "classification_confidence_ai": 0.2,
                "opportunity_score": 35,
            }
        ]
    )

    assert calls["n"] == 0
    assert enriched[0].get("industry") in (None, "")
    assert ctx.metrics["company_enrichment_candidates_total"] == 0

def test_company_enrichment_service_normalizes_legacy_product_company_type():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30,
                "allowed_company_types": ["end_client"],
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
        return {
            "organization": {
                "industry": "Software",
                "estimated_num_employees": "51-200",
                "linkedin_url": "https://linkedin.com/company/productco",
                "short_description": "Builds products",
            }
        }

    client.enrich_company_by_domain = fake_enrich

    service = CompanyEnrichmentService(ctx, control)

    enriched = service.enrich_companies(
        [
            {
                "company_key": "cmp_product",
                "company_display": "Product Co",
                "resolved_domain": "productco.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "product_company",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 35,
            }
        ]
    )

    assert calls["n"] == 1
    assert enriched[0]["industry"] == "Software"
    assert enriched[0]["enrichment_source"] == "apollo"


def test_company_enrichment_service_normalizes_legacy_outsourcing_type_and_skips_it():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30,
                "allowed_company_types": ["end_client"],
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

    enriched = service.enrich_companies(
        [
            {
                "company_key": "cmp_outsourcing",
                "company_display": "Outsource Co",
                "resolved_domain": "outsourceco.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "outsourcing",
                "classification_confidence_ai": 0.95,
                "opportunity_score": 35,
            }
        ]
    )

    assert calls["n"] == 0
    assert enriched[0].get("industry") in (None, "")
    assert ctx.metrics["company_enrichment_candidates_total"] == 0

def test_company_enrichment_service_uses_extracted_name_from_title_when_display_is_non_actionable():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30,
                "allowed_company_types": ["end_client"],
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
        return {
            "organization": {
                "industry": "Software",
                "estimated_num_employees": "51-200",
                "linkedin_url": "https://linkedin.com/company/tenaris",
                "short_description": "Energy technology company",
            }
        }

    client.enrich_company_by_domain = fake_enrich

    service = CompanyEnrichmentService(ctx, control)

    enriched = service.enrich_companies(
        [
            {
                "company_key": "cmp_tenaris",
                "company_display": "Empresa Confidencial",
                "title": "Backend Engineer at Tenaris",
                "resolved_domain": "tenaris.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.97,
                "opportunity_score": 40,
            }
        ]
    )

    assert calls["n"] == 1
    assert enriched[0]["industry"] == "Software"
    assert enriched[0]["enrichment_source"] == "apollo"


def test_company_enrichment_service_skips_suspicious_beta_domain_even_if_end_client_fallback_matches():
    ctx = RunContext.create(
        config={
            "database": {"path": ":memory:"},
            "providers": {
                "limits": {"apollo": 5},
                "clients": {"apollo": {"api_key": "fake-key"}},
            },
            "enrichment": {
                "apollo_company_ttl_days": 30,
                "allowed_company_types": ["end_client"],
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

    enriched = service.enrich_companies(
        [
            {
                "company_key": "cmp_beta",
                "company_display": "Rimutee",
                "resolved_domain": "beta.rimutee.com",
                "domain_validation_status": "accepted",
                "company_type_ai": "end_client",
                "classification_confidence_ai": 0.97,
                "opportunity_score": 35,
                "company_description": "Remote talent platform",
            }
        ]
    )

    assert calls["n"] == 0
    assert enriched[0].get("industry") in (None, "")
    assert ctx.metrics["company_enrichment_candidates_total"] == 0

