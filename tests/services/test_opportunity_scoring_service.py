from oie.orchestration.run_context import RunContext
from oie.services.opportunity_scoring_service import OpportunityScoringService


def test_opportunity_scoring_service_scores_and_sorts_companies():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_a",
            "company_display": "Acme",
            "total_openings": 3,
            "remote_jobs": 2,
            "contractor_jobs": 1,
            "multi_source_signal": True,
            "company_type_ai": "end_client",
        },
        {
            "company_key": "cmp_b",
            "company_display": "Beta",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "job_board",
        },
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 2

    assert scored[0]["company_key"] == "cmp_a"
    assert scored[0]["score_openings"] == 24
    assert scored[0]["score_remote"] == 8
    assert scored[0]["score_contractor"] == 6
    assert scored[0]["score_multi_source"] == 10
    assert scored[0]["score_company_type"] == 20
    assert scored[0]["opportunity_score"] == 68

    assert scored[1]["company_key"] == "cmp_b"
    assert scored[1]["score_openings"] == 8
    assert scored[1]["score_remote"] == 0
    assert scored[1]["score_contractor"] == 0
    assert scored[1]["score_multi_source"] == 0
    assert scored[1]["score_company_type"] == -10
    assert scored[1]["opportunity_score"] == -2

    assert ctx.metrics["companies_scored"] == 2
    assert ctx.metrics["scoring_completed"] is True


def test_opportunity_scoring_service_caps_components():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_cap",
            "company_display": "Cap Co",
            "total_openings": 20,
            "remote_jobs": 10,
            "contractor_jobs": 10,
            "multi_source_signal": True,
            "company_type_ai": "consulting",
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["score_openings"] == 40
    assert scored[0]["score_remote"] == 20
    assert scored[0]["score_contractor"] == 20
    assert scored[0]["score_multi_source"] == 10
    assert scored[0]["score_company_type"] == 10
    assert scored[0]["opportunity_score"] == 100


def test_opportunity_scoring_service_supports_legacy_company_type_aliases():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_product",
            "company_display": "Product Co",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "product_company",
        },
        {
            "company_key": "cmp_staffing",
            "company_display": "Staffing Co",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "staffing_agency",
        },
    ]

    scored = {row["company_key"]: row for row in service.score_companies(companies)}

    assert scored["cmp_product"]["score_company_type"] == 20
    assert scored["cmp_staffing"]["score_company_type"] == 5
