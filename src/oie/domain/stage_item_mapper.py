from __future__ import annotations

from oie.domain.entities import OpportunityCandidate
from oie.domain.serialization import to_primitive
from oie.orchestration.stage_item import StageItem


def candidate_to_stage_item(candidate: OpportunityCandidate) -> StageItem:
    payload = to_primitive(candidate)
    return {
        "id": str(payload["id"]),
        "value": payload,
        "metadata": {
            "domain_type": "OpportunityCandidate",
        },
    }
