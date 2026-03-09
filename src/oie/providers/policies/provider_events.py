from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ProviderEvent:
    provider: str
    event_type: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
