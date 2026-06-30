"""Domain layer for Opportunity Intelligence Engine.

This package contains business entities and value objects that should remain
independent from API, orchestration, and persistence adapters.
"""

from oie.domain.configuration import (
    AccountConfiguration,
    HubSpotDeliveryConfiguration,
    ICPProfile,
    QueryConfiguration,
    RunConfiguration,
    UserConfiguration,
)
from oie.domain.entities import (
    CRMProfile,
    CompanyProfile,
    Decision,
    DecisionHistory,
    Evidence,
    JobPosting,
    OpportunityCandidate,
    OpportunityScore,
)
from oie.domain.serialization import to_primitive
from oie.domain.value_objects import (
    CompanyId,
    DecisionId,
    JobId,
    LeadId,
    OpportunityId,
    StableId,
)

__all__ = [
    "AccountConfiguration",
    "CRMProfile",
    "CompanyId",
    "CompanyProfile",
    "Decision",
    "DecisionHistory",
    "DecisionId",
    "Evidence",
    "HubSpotDeliveryConfiguration",
    "ICPProfile",
    "JobId",
    "JobPosting",
    "LeadId",
    "OpportunityCandidate",
    "OpportunityId",
    "OpportunityScore",
    "QueryConfiguration",
    "RunConfiguration",
    "StableId",
    "UserConfiguration",
    "to_primitive",
]
