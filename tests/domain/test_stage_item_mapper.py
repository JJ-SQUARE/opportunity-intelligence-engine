from oie.domain.entities import JobPosting, OpportunityCandidate
from oie.domain.stage_item_mapper import candidate_to_stage_item, job_dict_to_candidate, stage_item_to_candidate
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


def test_stage_item_to_candidate_restores_candidate_object():
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
    restored = stage_item_to_candidate(item)

    assert restored.id == "opp_123"
    assert restored.source_job is not None
    assert restored.source_job.id == "job_456"
    assert restored.source_job.title == "Senior Python Engineer"
    assert restored.metadata == {"source": "unit-test"}


def test_job_dict_to_candidate_creates_candidate_from_raw_job():
    candidate = job_dict_to_candidate(
        {
            "title": "Senior Python Engineer",
            "company": "Acme",
            "job_url": "https://example.com/jobs/123",
            "source": "serpapi",
        },
        fallback_id="fallback_1",
    )

    assert str(candidate.id) == "opp_https___example_com_jobs_123"
    assert candidate.source_job is not None
    assert str(candidate.source_job.id) == "job_https___example_com_jobs_123"
    assert candidate.source_job.title == "Senior Python Engineer"
    assert candidate.source_job.company == "Acme"
    assert candidate.metadata["raw_job"]["source"] == "serpapi"
