from oie.orchestration.run_context import RunContext
from oie.services.company_identity_service import CompanyIdentityService


def test_normalize_company_name_removes_legal_suffixes():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    normalized = service.normalize_company_name("Acme, Inc.")

    assert normalized == "acme"


def test_normalize_company_name_handles_ampersand():
    ctx = RunContext.create(config={})
    service = CompanyIdentityService(ctx)

    normalized = service.normalize_company_name("Smith & Partners LLC")

    assert normalized == "smith and partners"
