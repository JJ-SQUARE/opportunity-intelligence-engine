from __future__ import annotations

from dataclasses import asdict, dataclass, field

from oie.orchestration.json_payload import JSONPayload


@dataclass
class ProviderEventRecord:
    provider: str
    event_type: str
    status_code: int | None = None
    message: str | None = None
    metadata: JSONPayload = field(default_factory=dict)

    def to_dict(self) -> JSONPayload:
        return asdict(self)
