from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JSONDict = dict[str, Any]


@dataclass(slots=True)
class AccountConfiguration:
    account_id: str | None = None
    account_name: str | None = None
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class UserConfiguration:
    user_id: str | None = None
    email: str | None = None
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class HubSpotDeliveryConfiguration:
    hubspot_user_id: str | None = None
    hubspot_owner_id: str | None = None
    hubspot_company_id: str | None = None
    hubspot_credentials_ref: str | None = None
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class ICPProfile:
    profile_id: str
    name: str
    weights: JSONDict = field(default_factory=dict)
    rules: JSONDict = field(default_factory=dict)
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class QueryConfiguration:
    query: str
    source: str | None = None
    location: str | None = None
    metadata: JSONDict = field(default_factory=dict)


@dataclass(slots=True)
class RunConfiguration:
    account: AccountConfiguration = field(default_factory=AccountConfiguration)
    user: UserConfiguration = field(default_factory=UserConfiguration)
    hubspot_delivery: HubSpotDeliveryConfiguration = field(
        default_factory=HubSpotDeliveryConfiguration
    )
    icp_profiles: list[ICPProfile] = field(default_factory=list)
    queries: list[QueryConfiguration] = field(default_factory=list)
    flags: JSONDict = field(default_factory=dict)
    mode: str = "default"
    metadata: JSONDict = field(default_factory=dict)
