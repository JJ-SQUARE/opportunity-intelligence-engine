from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StableId:
    value: str

    prefix: str = ""

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise ValueError(f"{self.__class__.__name__} value is required")
        if self.prefix and not normalized.startswith(f"{self.prefix}_"):
            raise ValueError(
                f"{self.__class__.__name__} must start with '{self.prefix}_'"
            )
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class OpportunityId(StableId):
    prefix: str = "opp"


@dataclass(frozen=True, slots=True)
class CompanyId(StableId):
    prefix: str = "comp"


@dataclass(frozen=True, slots=True)
class JobId(StableId):
    prefix: str = "job"


@dataclass(frozen=True, slots=True)
class LeadId(StableId):
    prefix: str = "lead"


@dataclass(frozen=True, slots=True)
class DecisionId(StableId):
    prefix: str = "dec"
