from oie.orchestration.run_context import RunContext
from oie.services.market_segmentation_service import MarketSegmentationService


def test_market_segmentation_service_segments_companies():
    ctx = RunContext.create(config={}, flags={})
    service = MarketSegmentationService(ctx)

    companies = [
        {
            "company": "Realign LLC",
            "company_type_ai": "product_company",
            "industry_ai": "fintech",
            "sample_description": "Gen AI Strategy Lead, LLMs, cloud, RAG, architecture",
            "notes_ai": ["enterprise ai initiatives", "cloud ai services"],
            "score": 4,
            "vendor_acceptance_probability_ai": 75,
        },
        {
            "company": "TowardJobs",
            "company_type_ai": "unknown",
            "industry_ai": "market research",
            "sample_description": "survey focus groups data entry product testing",
            "notes_ai": ["work from home side gig"],
            "score": 6,
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
