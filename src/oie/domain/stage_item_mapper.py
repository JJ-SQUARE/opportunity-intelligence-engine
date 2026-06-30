from __future__ import annotations

from typing import Any

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
from oie.domain.value_objects import JobId, OpportunityId
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


def stage_item_to_candidate(item: StageItem) -> OpportunityCandidate:
    value = item.get("value")
    if not isinstance(value, dict):
        raise TypeError("StageItem value must be an OpportunityCandidate payload.")

    return OpportunityCandidate(
        id=str(value["id"]),
        source_job=_job_posting_from_payload(value.get("source_job")),
        company=_company_profile_from_payload(value.get("company")),
        contacts=list(value.get("contacts") or []),
        crm_profile=_crm_profile_from_payload(value.get("crm_profile")),
        decision_history=_decision_history_from_payload(value.get("decision_history")),
        scores=_opportunity_scores_from_payload(value.get("scores")),
        evidence=_evidence_list_from_payload(value.get("evidence")),
        metadata=dict(value.get("metadata") or {}),
        artifacts=dict(value.get("artifacts") or {}),
    )


def _job_posting_from_payload(payload: Any) -> JobPosting | None:
    if not isinstance(payload, dict):
        return None
    return JobPosting(**payload)


def _company_profile_from_payload(payload: Any) -> CompanyProfile | None:
    if not isinstance(payload, dict):
        return None
    return CompanyProfile(**payload)


def _crm_profile_from_payload(payload: Any) -> CRMProfile | None:
    if not isinstance(payload, dict):
        return None
    return CRMProfile(**payload)


def _evidence_list_from_payload(payload: Any) -> list[Evidence]:
    if not isinstance(payload, list):
        return []
    return [
        Evidence(**item)
        for item in payload
        if isinstance(item, dict)
    ]


def _opportunity_scores_from_payload(payload: Any) -> list[OpportunityScore]:
    if not isinstance(payload, list):
        return []
    return [
        OpportunityScore(**item)
        for item in payload
        if isinstance(item, dict)
    ]


def _decision_history_from_payload(payload: Any) -> DecisionHistory:
    if not isinstance(payload, dict):
        return DecisionHistory()

    decisions = []
    for item in payload.get("decisions") or []:
        if not isinstance(item, dict):
            continue
        decision_payload = dict(item)
        decision_payload["evidence"] = _evidence_list_from_payload(
            decision_payload.get("evidence")
        )
        decisions.append(Decision(**decision_payload))

    return DecisionHistory(decisions=decisions)


def job_dict_to_candidate(job: dict[str, Any], fallback_id: str) -> OpportunityCandidate:
    job_id = _first_non_empty(job, ("job_id", "id", "job_url", "apply_url"), fallback_id)
    candidate_id = job_id

    return OpportunityCandidate(
        id=OpportunityId(candidate_id),
        source_job=JobPosting(
            id=JobId(job_id),
            title=str(job.get("title") or ""),
            company=str(job.get("company") or ""),
            location=job.get("location"),
            job_url=job.get("job_url"),
            apply_url=job.get("apply_url"),
            description=job.get("description"),
            source=job.get("source"),
            detected_at=job.get("detected_at"),
        ),
        metadata={
            "raw_job": dict(job),
        },
    )


def _first_non_empty(
    payload: dict[str, Any],
    keys: tuple[str, ...],
    fallback: str,
) -> str:
    for key in keys:
        value = str(payload.get(key) or "").strip()
        if value:
            return _stable_token(value)
    return _stable_token(fallback)


def _stable_token(value: str) -> str:
    return "".join(
        character if character.isalnum() else "_"
        for character in value.strip().lower()
    ).strip("_")
