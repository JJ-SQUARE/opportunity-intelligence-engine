from oie.orchestration.run_context import RunContext
from oie.services.opportunity_scoring_service import OpportunityScoringService


def test_opportunity_scoring_service_scores_and_sorts_companies():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_display": "High Value Co",
            "total_openings": 5,
            "remote_jobs": 3,
            "contractor_jobs": 2,
            "multi_source_signal": True,
            "company_type_ai": "end_client",
        },
        {
            "company_display": "Lower Value Co",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "unknown",
        },
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 2
    assert scored[0]["company_display"] == "High Value Co"
    assert scored[0]["score_openings"] == 40
    assert scored[0]["score_remote"] == 12
    assert scored[0]["score_contractor"] == 12
    assert scored[0]["score_multi_source"] == 10
    assert scored[0]["score_company_type"] == 20
    assert scored[0]["opportunity_score"] == 94

    assert scored[1]["company_display"] == "Lower Value Co"
    assert ctx.metrics["companies_scored"] == 2
    assert ctx.metrics["scoring_completed"] is True


def test_opportunity_scoring_service_applies_negative_weight_for_job_board():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_display": "Aggregator",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "job_board",
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["score_company_type"] == -10
    assert scored[0]["opportunity_score"] == -2
