from __future__ import annotations

from typing import Any, Dict, List

from oie.collectors.base import BaseJobCollector


class CollectorRegistry:
    def __init__(self) -> None:
        self._collectors: Dict[str, BaseJobCollector] = {}

    def register(self, collector: BaseJobCollector) -> None:
        self._collectors[collector.collector_name] = collector

    def get(self, name: str) -> BaseJobCollector | None:
        return self._collectors.get(name)

    def all(self) -> List[BaseJobCollector]:
        return list(self._collectors.values())

    def enabled(self, enabled_names: List[str] | None = None) -> List[BaseJobCollector]:
        if not enabled_names:
            return self.all()
        enabled_set = set(enabled_names)
        return [collector for collector in self.all() if collector.collector_name in enabled_set]
