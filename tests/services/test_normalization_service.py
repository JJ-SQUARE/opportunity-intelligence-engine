from oie.orchestration.run_context import RunContext
from oie.services.normalization_service import NormalizationService


def test_normalization_service_detects_remote_and_contract_signals():
    ctx = RunContext.create(config={}, flags={})
    service = NormalizationService(ctx)

    jobs = [
        {
            "company": "Acme",
            "location": "Anywhere",
            "description": (
                "Trabajo 100% remoto. Tipo de contrato: Prestación de servicios. "
                "Proyecto freelance con horario flexible."
            ),
            "source_meta": {
                "query_text": "desarrollador remoto",
            },
        }
    ]

    result = service.normalize(jobs)

    assert len(result) == 1
    assert result[0]["is_remote"] is True
    assert result[0]["is_contractor"] is True
    assert result[0]["is_full_time"] is False


def test_normalization_service_detects_full_time_remote_from_extensions():
    ctx = RunContext.create(config={}, flags={})
    service = NormalizationService(ctx)

    jobs = [
        {
            "company": "Beta",
            "location": "Mexico",
            "description": "Python role",
            "raw": {
                "extensions": ["Work from home", "Full-time"],
                "detected_extensions": {
                    "work_from_home": True,
                    "schedule_type": "Full-time",
                },
            },
        }
    ]

    result = service.normalize(jobs)

    assert len(result) == 1
    assert result[0]["is_remote"] is True
    assert result[0]["is_full_time"] is True
