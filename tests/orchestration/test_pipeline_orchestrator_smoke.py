from oie.orchestration.run_context import RunContext
from oie.orchestration.pipeline_orchestrator import PipelineOrchestrator


def test_orchestrator_has_initial_stages():
    ctx = RunContext.create(config={})
    orchestrator = PipelineOrchestrator(ctx)

    assert orchestrator.collection_service is not None
    assert orchestrator.normalization_service is not None
    assert orchestrator.job_dedup_service is not None
    assert orchestrator.hiring_signals_service is not None
    assert orchestrator.company_identity_service is not None
    assert orchestrator.domain_resolution_service is not None
    assert orchestrator.opportunity_scoring_service is not None
    assert orchestrator.persistence_service is not None
    assert orchestrator.provider_control_service is not None
