from oie.orchestration.run_context import RunContext
from oie.services.company_identity_service import CompanyIdentityService
from oie.services.persistence_service import PersistenceService


def test_normalize_company_name_removes_legal_suffixes():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    normalized = service.normalize_company_name("Acme, Inc.")

    assert normalized == "acme"


def test_normalize_company_name_handles_ampersand():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    normalized = service.normalize_company_name("Smith & Partners LLC")

    assert normalized == "smith and partners"


def test_normalize_company_root_removes_generic_business_terms():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    root = service.normalize_company_root("Acme Technologies LLC")

    assert root == "acme"


def test_enrich_company_identity_builds_company_key_and_merge_candidates():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    companies = [
        {
            "company": "Acme Technologies LLC",
            "resolved_domain": "acme.com",
            "total_openings": 2,
            "sources": ["google_jobs"],
        },
        {
            "company": "Acme Inc.",
            "resolved_domain": "acme.com",
            "total_openings": 1,
            "sources": ["linkedin_jobs"],
        },
    ]

    enriched = service.enrich_company_identity(companies)

    assert len(enriched) == 2
    assert enriched[0]["company_key"].startswith("cmp_")
    assert ctx.metrics["company_merge_candidates_detected"] >= 1


def test_manual_aliases_are_added_to_company_identity():
    ctx = RunContext.create(
        config={
            "company_identity": {
                "manual_aliases": {
                    "Meta Platforms": ["Meta", "Facebook"]
                }
            }
        }
    )
    service = CompanyIdentityService(ctx)

    companies = [
        {
            "company": "Meta Platforms Inc.",
            "resolved_domain": "meta.com",
            "sources": ["google_jobs"],
        }
    ]

    enriched = service.enrich_company_identity(companies)

    assert "Meta" in enriched[0]["aliases"]
    assert "Facebook" in enriched[0]["aliases"]


def test_reconcile_existing_company_key_by_normalized_and_domain(tmp_path):
    db_path = tmp_path / "oie_test.db"

    seed_ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    seed_service = PersistenceService(seed_ctx)
    seed_service.persist_run_snapshot(
        status="ok",
        companies=[
            {
                "company_key": "cmp_existing",
                "company_display": "Acme Inc.",
                "company_normalized": "acme",
                "resolved_domain": "acme.com",
                "domain_source": "apply_url",
                "domain_confidence": 0.9,
                "aliases": ["Acme Inc."],
                "alias_type_map": {
                    "Acme Inc.": "acme",
                    "Acme Inc.__type": "observed_name",
                },
            }
        ],
    )

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    service = CompanyIdentityService(ctx)

    companies = [
        {
            "company": "Acme LLC",
            "resolved_domain": "acme.com",
            "sources": ["linkedin_jobs"],
        }
    ]

    enriched = service.enrich_company_identity(companies)

    assert enriched[0]["company_key"] == "cmp_existing"
    assert ctx.metrics["company_identity_reused_by_normalized_domain"] == 1


def test_reconcile_existing_company_key_by_alias(tmp_path):
    db_path = tmp_path / "oie_test.db"

    seed_ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    seed_service = PersistenceService(seed_ctx)
    seed_service.persist_run_snapshot(
        status="ok",
        companies=[
            {
                "company_key": "cmp_meta",
                "company_display": "Meta Platforms Inc.",
                "company_normalized": "meta platforms",
                "resolved_domain": "meta.com",
                "domain_source": "apply_url",
                "domain_confidence": 0.9,
                "aliases": ["Meta Platforms Inc.", "Facebook"],
                "alias_type_map": {
                    "Meta Platforms Inc.": "meta platforms",
                    "Meta Platforms Inc.__type": "observed_name",
                    "Facebook": "facebook",
                    "Facebook__type": "manual_alias",
                },
            }
        ],
    )

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    service = CompanyIdentityService(ctx)

    companies = [
        {
            "company": "Facebook",
            "resolved_domain": None,
            "sources": ["google_jobs"],
        }
    ]

    enriched = service.enrich_company_identity(companies)

    assert enriched[0]["company_key"] == "cmp_meta"
    assert ctx.metrics["company_identity_reused_by_alias"] == 1


def test_enrich_company_identity_treats_confidential_company_as_placeholder():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    enriched = service.enrich_company_identity(
        [
            {
                "company": "Empresa Confidencial",
                "resolved_domain": "secret.example.com",
                "title": "Backend Engineer",
                "job_url": "https://example.com/jobs/1",
                "sources": ["google_jobs"],
            }
        ]
    )

    assert enriched[0]["company_display"] == "unknown"
    assert enriched[0]["company_key"].startswith("cmp_placeholder_")


def test_detect_merge_candidates_does_not_merge_same_root_with_conflicting_domains():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    candidates = service.detect_merge_candidates(
        [
            {
                "company_key": "cmp_1",
                "company_display": "Focus Digital MX",
                "company_normalized": "focus digital mx",
                "company_root": "focus mx",
                "resolved_domain": "focusmx.com",
            },
            {
                "company_key": "cmp_2",
                "company_display": "Focus Digital AR",
                "company_normalized": "focus digital ar",
                "company_root": "focus ar",
                "resolved_domain": "focusar.com",
            },
        ]
    )

    assert candidates == []

def test_enrich_company_identity_uses_shared_extractor_for_unknown_company_display():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    enriched = service.enrich_company_identity(
        [
            {
                "company": "unknown",
                "title": "Backend Engineer at Tenaris",
                "description": "",
                "apply_url": "",
                "resolved_domain": "tenaris.com",
                "sources": ["google_jobs"],
            }
        ]
    )

    assert len(enriched) == 1
    assert enriched[0]["company_display"] == "Tenaris"
    assert enriched[0]["company_normalized"] == "tenaris"


def test_enrich_company_identity_does_not_infer_company_from_blocked_apply_url_only():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    enriched = service.enrich_company_identity(
        [
            {
                "company": "unknown",
                "title": "Senior Backend Engineer",
                "description": "",
                "apply_url": "https://empresa-confidencial.gupy.io/jobs/12345",
                "resolved_domain": None,
                "sources": ["google_jobs"],
            }
        ]
    )

    assert len(enriched) == 1
    assert enriched[0]["company_display"] == "unknown"
    assert enriched[0]["company_key"].startswith("cmp_placeholder_")

def test_detect_merge_candidates_does_not_merge_placeholder_or_unknown_names():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    candidates = service.detect_merge_candidates(
        [
            {
                "company_key": "cmp_placeholder_1",
                "company_display": "unknown",
                "company_normalized": "unknown",
                "company_root": "unknown",
                "resolved_domain": "",
            },
            {
                "company_key": "cmp_placeholder_2",
                "company_display": "unknown",
                "company_normalized": "unknown",
                "company_root": "unknown",
                "resolved_domain": "",
            },
        ]
    )

    assert candidates == []


def test_detect_merge_candidates_does_not_merge_unrelated_names_even_with_same_domain():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    candidates = service.detect_merge_candidates(
        [
            {
                "company_key": "cmp_1",
                "company_display": "Alpha Security",
                "company_normalized": "alpha security",
                "company_root": "alpha security",
                "resolved_domain": "example.com",
            },
            {
                "company_key": "cmp_2",
                "company_display": "Beta Logistics",
                "company_normalized": "beta logistics",
                "company_root": "beta logistics",
                "resolved_domain": "example.com",
            },
        ]
    )

    assert candidates == []


def test_detect_merge_candidates_keeps_same_domain_when_brand_is_really_the_same():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    candidates = service.detect_merge_candidates(
        [
            {
                "company_key": "cmp_1",
                "company_display": "Acme Inc.",
                "company_normalized": "acme",
                "company_root": "acme",
                "resolved_domain": "acme.com",
            },
            {
                "company_key": "cmp_2",
                "company_display": "Acme LLC",
                "company_normalized": "acme",
                "company_root": "acme",
                "resolved_domain": "acme.com",
            },
        ]
    )

    assert len(candidates) == 1
    assert candidates[0]["reason"] in {"same_company_normalized", "same_company_root_and_domain", "same_domain"}


def test_detect_merge_candidates_does_not_merge_same_domain_with_single_weak_shared_token():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    candidates = service.detect_merge_candidates(
        [
            {
                "company_key": "cmp_1",
                "company_display": "Nova Security",
                "company_normalized": "nova security",
                "company_root": "nova security",
                "resolved_domain": "example.com",
            },
            {
                "company_key": "cmp_2",
                "company_display": "Nova Logistics",
                "company_normalized": "nova logistics",
                "company_root": "nova logistics",
                "resolved_domain": "example.com",
            },
        ]
    )

    assert candidates == []


def test_detect_merge_candidates_allows_same_domain_when_one_name_contains_the_other():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    candidates = service.detect_merge_candidates(
        [
            {
                "company_key": "cmp_1",
                "company_display": "Tekton",
                "company_normalized": "tekton",
                "company_root": "tekton",
                "resolved_domain": "tektonlabs.com",
            },
            {
                "company_key": "cmp_2",
                "company_display": "Tekton Labs",
                "company_normalized": "tekton labs",
                "company_root": "tekton",
                "resolved_domain": "tektonlabs.com",
            },
        ]
    )

    assert len(candidates) == 1


def test_enrich_company_identity_adds_observed_alias_when_extracted_name_differs():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    enriched = service.enrich_company_identity(
        [
            {
                "company": "unknown",
                "title": "Backend Engineer at Tenaris",
                "description": "",
                "apply_url": "",
                "resolved_domain": "tenaris.com",
                "sources": ["google_jobs"],
            }
        ]
    )

    assert enriched[0]["company_display"] == "Tenaris"
    assert "Tenaris" in enriched[0]["aliases"]
    assert enriched[0]["alias_type_map"]["Tenaris"] == "tenaris"
    assert enriched[0]["alias_type_map"]["Tenaris__type"] == "observed_name"


def test_build_aliases_does_not_keep_unknown_or_placeholder_aliases():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    aliases, alias_type_map = service.build_aliases(
        "Tenaris",
        "tenaris",
        observed_candidates=["unknown", "Empresa Confidencial", "Tenaris"],
    )

    assert aliases == ["Tenaris"]
    assert "unknown" not in alias_type_map
    assert "Empresa Confidencial" not in alias_type_map

def test_reconcile_existing_company_key_by_unique_normalized_without_domain(tmp_path):
    db_path = tmp_path / "oie_test.db"

    seed_ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    seed_service = PersistenceService(seed_ctx)
    seed_service.persist_run_snapshot(
        status="ok",
        companies=[
            {
                "company_key": "cmp_existing_normalized",
                "company_display": "Acme Inc.",
                "company_normalized": "acme",
                "resolved_domain": "acme.com",
                "aliases": [],
                "alias_type_map": {},
            }
        ],
    )

    ctx = RunContext.create(
        config={"database": {"path": str(db_path)}},
        flags={},
    )
    service = CompanyIdentityService(ctx)

    enriched = service.enrich_company_identity(
        [
            {
                "company": "Acme",
                "resolved_domain": None,
                "sources": ["google_jobs"],
            }
        ]
    )

    assert enriched[0]["company_key"] == "cmp_existing_normalized"
    assert ctx.metrics["company_identity_reused_by_normalized_unique"] == 1
