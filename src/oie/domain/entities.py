from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

JSONDict = dict[str, Any]


@dataclass(slots=True)
class JobPosting:
    title: str
    company: str
    location: str | None = None
    job_url: str | None = None
    apply_url: str | None = None
    description: str | None = None
    source: str | None = None
    detected_at: str | None = None


@dataclass(slots=True)
class CompanyProfile:
    company_display: str
    company_normalized: str
    resolved_domain: str | None = None
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class CRMProfile:
    provider: str | None = None
    company_id: str | None = None
    owner_id: str | None = None
    lifecycle_stage: str | None = None
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class Evidence:
    source: str
    value: str
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class OpportunityScore:
    score: float
    label: str | None = None
    reasons: list[str] = field(default_factory=list)
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class Decision:
    stage: str
    decision: str
    confidence: float
    reason: str
    evidence: list[Evidence] = field(default_factory=list)
    timestamp: str | None = None
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class DecisionHistory:
    decisions: list[Decision] = field(default_factory=list)

    def add(self, decision: Decision) -> None:
        self.decisions.append(decision)


@dataclass(slots=True)
class OpportunityCandidate:
    id: str
    source_job: JobPosting | None = None
    company: CompanyProfile | None = None
    contacts: list[JSONDict] = field(default_factory=list)
    crm_profile: CRMProfile | None = None
    decision_history: DecisionHistory = field(default_factory=DecisionHistory)
    scores: list[OpportunityScore] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    metadata: JSONDict = field(default_factory=dict)
    artifacts: JSONDict = field(default_factory=dict)
