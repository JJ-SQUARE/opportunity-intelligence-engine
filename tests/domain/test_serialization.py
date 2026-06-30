from oie.domain.entities import (
    CompanyProfile,
    Decision,
    Evidence,
    JobPosting,
    OpportunityCandidate,
)
from oie.domain.serialization import to_primitive
from oie.domain.value_objects import CompanyId, JobId, OpportunityId


def test_to_primitive_serializes_candidate_to_json_safe_dict():
    candidate = OpportunityCandidate(
        id=OpportunityId("opp_123"),
        source_job=JobPosting(
            id=JobId("job_456"),
            title="Senior Python Engineer",
            company="Acme",
        ),
        company=CompanyProfile(
            id=CompanyId("comp_acme"),
            company_display="Acme",
            company_normalized="acme",
        ),
        evidence=[Evidence(source="job", value="Hiring signal")],
    )
    candidate.decision_history.add(
        Decision(
            stage="company_gate",
            decision="accepted",
            confidence=0.9,
            reason="Real company",
        )
    )

    payload = to_primitive(candidate)

    assert payload["id"] == "opp_123"
    assert payload["source_job"]["id"] == "job_456"
    assert payload["company"]["id"] == "comp_acme"
    assert payload["evidence"] == [
        {
            "source": "job",
            "value": "Hiring signal",
            "metadata": {},
        }
    ]
    assert payload["decision_history"]["decisions"][0]["decision"] == "accepted"


def test_to_primitive_preserves_plain_stage_item_shapes():
    item = {
        "id": "item_1",
        "value": {"nested": OpportunityId("opp_nested")},
        "metadata": {"source": "test"},
    }

    assert to_primitive(item) == {
        "id": "item_1",
        "value": {"nested": "opp_nested"},
        "metadata": {"source": "test"},
    }
