from __future__ import annotations

from typing import Any, Dict


class ProviderClient:
    provider_name = "base"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def request(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("ProviderClient.request must be implemented")