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
from oie.domain.stage_item_mapper import candidate_to_stage_item, job_dict_to_candidate, stage_item_to_candidate
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
    "candidate_to_stage_item",
    "job_dict_to_candidate",
    "stage_item_to_candidate",
    "to_primitive",
]
