from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseJobCollector(ABC):
    collector_name: str = "base"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}

    @abstractmethod
    def collect(self) -> List[Dict[str, Any]]:
        raise NotImplementedError
