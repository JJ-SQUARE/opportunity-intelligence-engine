from oie.orchestration.run_context import RunContext
from oie.services.market_segmentation_service import MarketSegmentationService


def test_market_segmentation_service_segments_companies():
    ctx = RunContext.create(config={}, flags={})
    service = MarketSegmentationService(ctx)

    companies = [
        {
            "company": "Realign LLC",
            "company_display": "Realign LLC",
            "company_type_ai": "end_client",
            "industry": "fintech",
            "company_description": "Gen AI Strategy Lead, LLMs, cloud, RAG, architecture",
            "notes_ai": ["enterprise ai initiatives", "cloud ai services"],
            "opportunity_score": 84,
            "vendor_acceptance_probability_ai": 75,
        },
        {
            "company": "TowardJobs",
            "company_display": "TowardJobs",
            "company_type_ai": "unknown",
            "industry": "market research",
            "company_description": "survey focus groups data entry product testing",
            "notes_ai": ["work from home side gig"],
            "opportunity_score": 22,
            "vendor_acceptance_probability_ai": 40,
        },
    ]

    segmented = service.segment_companies(companies)
    summary = service.build_segment_summary(companies)

    realign = next(x for x in segmented if x["company"] == "Realign LLC")
    toward = next(x for x in segmented if x["company"] == "TowardJobs")

    assert realign["market_segment"] == "tech_product_hiring"
    assert toward["market_segment"] == "gig_remote_labor"
    assert len(summary) >= 2

    tech_summary = next(x for x in summary if x["market_segment"] == "tech_product_hiring")
    assert tech_summary["companies"] == 1
    assert tech_summary["avg_score"] == 84.0
    assert "Realign LLC" in tech_summary["top_examples"]
