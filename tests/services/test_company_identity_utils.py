from oie.utils.company_identity_utils import (
    is_actionable_company_name,
    is_non_actionable_company_name,
)


def test_non_actionable_company_names_are_rejected():
    assert is_non_actionable_company_name("Confidencial") is True
    assert is_non_actionable_company_name("Confidential") is True
    assert is_non_actionable_company_name("Importante empresa") is True
    assert is_non_actionable_company_name("Empresa del sector") is True
    assert is_non_actionable_company_name("Stealth startup") is True
    assert is_non_actionable_company_name("") is True


def test_actionable_company_names_are_allowed():
    assert is_actionable_company_name("Tenaris") is True
    assert is_actionable_company_name("Sofka Technologies") is True
    assert is_actionable_company_name("Quid Solutions") is True
