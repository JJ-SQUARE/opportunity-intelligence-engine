from __future__ import annotations

from typing import Any, Dict, Optional

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import (
    ProviderExecutionBlockedError,
    ProviderExecutionError,
    ProviderExecutionService,
)


class SerpAPISearchService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(
            ctx, provider_control_service
        )

    def search_google_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        num: int = 10,
    ) -> Dict[str, Any]:
        client = self.provider_control_service.registry.get_client("serpapi")
        if client is None:
            self.ctx.metrics["serpapi_search_skipped_no_client"] = True
            self.ctx.metrics["serpapi_search_google_jobs_skipped_no_client"] = True
            return {}

        try:
            result = self.provider_execution_service.execute(
                "serpapi",
                "search_google_jobs",
                client.search_google_jobs,
                query,
                location=location,
                num=num,
                cost=1,
            )
        except ProviderExecutionBlockedError:
            self.ctx.metrics["serpapi_search_skipped_blocked"] = True
            self.ctx.metrics["serpapi_search_google_jobs_skipped_blocked"] = True
            return {}
        except ProviderExecutionError as exc:
            self.ctx.metrics["serpapi_search_errors"] = (
                int(self.ctx.metrics.get("serpapi_search_errors", 0)) + 1
            )
            self.ctx.metrics["serpapi_search_google_jobs_errors"] = (
                int(self.ctx.metrics.get("serpapi_search_google_jobs_errors", 0)) + 1
            )
            self.ctx.add_provider_event(
                provider="serpapi",
                event_type="search_google_jobs_failed",
                message="serpapi_search_google_jobs_failed",
                metadata={
                    "query": query,
                    "location": location,
                    "num": num,
                    "error": repr(exc),
                },
            )
            return {}

        self.ctx.metrics["serpapi_search_requests"] = (
            int(self.ctx.metrics.get("serpapi_search_requests", 0)) + 1
        )
        self.ctx.metrics["serpapi_search_google_jobs_requests"] = (
            int(self.ctx.metrics.get("serpapi_search_google_jobs_requests", 0)) + 1
        )

        return result

    def search_google(
        self,
        query: str,
        num: int = 10,
    ) -> Dict[str, Any]:
        client = self.provider_control_service.registry.get_client("serpapi")
        if client is None:
            self.ctx.metrics["serpapi_search_skipped_no_client"] = True
            self.ctx.metrics["serpapi_search_google_skipped_no_client"] = True
            return {}

        try:
            result = self.provider_execution_service.execute(
                "serpapi",
                "search_google",
                client.search_google,
                query,
                num=num,
                cost=1,
            )
        except ProviderExecutionBlockedError:
            self.ctx.metrics["serpapi_search_skipped_blocked"] = True
            self.ctx.metrics["serpapi_search_google_skipped_blocked"] = True
            return {}
        except ProviderExecutionError as exc:
            self.ctx.metrics["serpapi_search_errors"] = (
                int(self.ctx.metrics.get("serpapi_search_errors", 0)) + 1
            )
            self.ctx.metrics["serpapi_search_google_errors"] = (
                int(self.ctx.metrics.get("serpapi_search_google_errors", 0)) + 1
            )
            self.ctx.add_provider_event(
                provider="serpapi",
                event_type="search_google_failed",
                message="serpapi_search_google_failed",
                metadata={
                    "query": query,
                    "num": num,
                    "error": repr(exc),
                },
            )
            return {}

        self.ctx.metrics["serpapi_search_requests"] = (
            int(self.ctx.metrics.get("serpapi_search_requests", 0)) + 1
        )
        self.ctx.metrics["serpapi_search_google_requests"] = (
            int(self.ctx.metrics.get("serpapi_search_google_requests", 0)) + 1
        )

        return result
