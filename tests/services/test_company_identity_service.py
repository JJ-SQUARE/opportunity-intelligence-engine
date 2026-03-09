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
