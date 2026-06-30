import pytest

from oie.domain.value_objects import (
    CompanyId,
    DecisionId,
    JobId,
    LeadId,
    OpportunityId,
)


def test_stable_ids_normalize_and_render_as_strings():
    assert str(OpportunityId("  opp_123  ")) == "opp_123"
    assert CompanyId("comp_acme").value == "comp_acme"
    assert JobId("job_456").value == "job_456"
    assert LeadId("lead_789").value == "lead_789"
    assert DecisionId("dec_001").value == "dec_001"


def test_stable_ids_reject_empty_values():
    with pytest.raises(ValueError, match="OpportunityId value is required"):
        OpportunityId("   ")


def test_stable_ids_reject_invalid_prefixes():
    with pytest.raises(ValueError, match="OpportunityId must start with 'opp_'"):
        OpportunityId("job_123")
