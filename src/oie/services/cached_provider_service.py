from __future__ import annotations

from typing import Any, Callable, Dict

from oie.orchestration.run_context import RunContext
from oie.services.http_cache_service import HTTPCacheService


class CachedProviderService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.cache = HTTPCacheService(ctx)

    def _bump_metric(self, key: str, amount: int = 1) -> None:
        self.ctx.metrics[key] = int(self.ctx.metrics.get(key, 0) or 0) + amount

    def _record_cache_hit(self, namespace: str) -> None:
        self._bump_metric("cached_provider_hits")
        self._bump_metric(f"{namespace}_cache_hits")

    def _record_cache_miss(self, namespace: str) -> None:
        self._bump_metric("cached_provider_misses")
        self._bump_metric(f"{namespace}_cache_misses")

    def _record_cache_write(self, namespace: str) -> None:
        self._bump_metric("cached_provider_writes")
        self._bump_metric(f"{namespace}_cache_writes")

    def execute_cached(
        self,
        namespace: str,
        cache_payload: Dict[str, Any],
        fn: Callable[..., Dict[str, Any]],
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        if self.ctx.flags.get("cache_only"):
            cached = self.cache.get(namespace, cache_payload)
            if cached is not None:
                self._record_cache_hit(namespace)
                return cached
            self._record_cache_miss(namespace)
            self.ctx.metrics["cache_only_misses"] = self.ctx.metrics.get("cache_only_misses", 0) + 1
            return {}

        cached = self.cache.get(namespace, cache_payload)
        if cached is not None:
            self._record_cache_hit(namespace)
            return cached

        self._record_cache_miss(namespace)
        result = fn(*args, **kwargs) or {}
        if isinstance(result, dict):
            self.cache.set(namespace, cache_payload, result)
            self._record_cache_write(namespace)
        return result
