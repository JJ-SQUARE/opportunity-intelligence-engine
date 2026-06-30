from oie.domain.entities import JobPosting, OpportunityCandidate
from oie.domain.stage_item_mapper import candidate_to_stage_item
from oie.domain.value_objects import JobId, OpportunityId


def test_candidate_to_stage_item_preserves_candidate_payload():
    candidate = OpportunityCandidate(
        id=OpportunityId("opp_123"),
        source_job=JobPosting(
            id=JobId("job_456"),
            title="Senior Python Engineer",
            company="Acme",
        ),
        metadata={"source": "unit-test"},
    )

    item = candidate_to_stage_item(candidate)

    assert item["id"] == "opp_123"
    assert item["metadata"] == {"domain_type": "OpportunityCandidate"}
    assert item["value"]["id"] == "opp_123"
    assert item["value"]["source_job"]["id"] == "job_456"
    assert item["value"]["metadata"] == {"source": "unit-test"}
