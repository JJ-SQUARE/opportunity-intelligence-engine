from __future__ import annotations

from dataclasses import dataclass

from oie.persistence.company_alias_repository import CompanyAliasRepository
from oie.persistence.company_merge_candidate_repository import CompanyMergeCandidateRepository
from oie.persistence.company_profile_repository import CompanyProfileRepository
from oie.persistence.company_repository import CompanyRepository
from oie.persistence.company_score_repository import CompanyScoreRepository
from oie.persistence.context import PersistenceContext
from oie.persistence.domain_repository import DomainRepository
from oie.persistence.job_repository import JobRepository
from oie.persistence.lead_repository import LeadRepository
from oie.persistence.provider_event_repository import ProviderEventRepository
from oie.persistence.provider_operation_metrics_repository import ProviderOperationMetricsRepository
from oie.persistence.run_metrics_repository import RunMetricsRepository
from oie.persistence.run_repository import RunRepository


@dataclass(frozen=True)
class RepositoryProvider:
    run_repository: RunRepository
    run_metrics_repository: RunMetricsRepository
    provider_event_repository: ProviderEventRepository
    provider_operation_metrics_repository: ProviderOperationMetricsRepository
    company_repository: CompanyRepository
    company_alias_repository: CompanyAliasRepository
    domain_repository: DomainRepository
    company_merge_candidate_repository: CompanyMergeCandidateRepository
    job_repository: JobRepository
    lead_repository: LeadRepository
    company_score_repository: CompanyScoreRepository
    company_profile_repository: CompanyProfileRepository

    @classmethod
    def from_persistence(
        cls,
        persistence: PersistenceContext,
    ) -> "RepositoryProvider":
        return cls(
            run_repository=RunRepository(persistence=persistence),
            run_metrics_repository=RunMetricsRepository(persistence=persistence),
            provider_event_repository=ProviderEventRepository(persistence=persistence),
            provider_operation_metrics_repository=ProviderOperationMetricsRepository(persistence=persistence),
            company_repository=CompanyRepository(persistence=persistence),
            company_alias_repository=CompanyAliasRepository(persistence=persistence),
            domain_repository=DomainRepository(persistence=persistence),
            company_merge_candidate_repository=CompanyMergeCandidateRepository(persistence=persistence),
            job_repository=JobRepository(persistence=persistence),
            lead_repository=LeadRepository(persistence=persistence),
            company_score_repository=CompanyScoreRepository(persistence=persistence),
            company_profile_repository=CompanyProfileRepository(persistence=persistence),
        )
