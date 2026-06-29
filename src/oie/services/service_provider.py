from __future__ import annotations

from dataclasses import dataclass

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.persistence.repository_provider import RepositoryProvider
from oie.services.persistence_service import PersistenceService
from oie.services.provider_control_service import ProviderControlService


@dataclass(frozen=True)
class ServiceProvider:
    ctx: RunContext
    persistence_service: PersistenceService
    persistence: PersistenceContext
    repositories: RepositoryProvider
    provider_control_service: ProviderControlService

    @classmethod
    def from_run_context(cls, ctx: RunContext) -> "ServiceProvider":
        persistence_service = PersistenceService(ctx)
        provider_control_service = ProviderControlService(ctx)
        return cls(
            ctx=ctx,
            persistence_service=persistence_service,
            persistence=persistence_service.persistence,
            repositories=persistence_service.repositories,
            provider_control_service=provider_control_service,
        )
