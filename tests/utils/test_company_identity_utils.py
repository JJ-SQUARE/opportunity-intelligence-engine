from oie.utils.company_identity_utils import (
    is_actionable_company_name,
    is_non_actionable_company_name,
)


def test_company_identity_utils_rejects_confidential_and_generic_names():
    assert is_non_actionable_company_name("Empresa Confidencial") is True
    assert is_non_actionable_company_name("Confidential Company") is True
    assert is_non_actionable_company_name("World") is True
    assert is_non_actionable_company_name("Global") is True


def test_company_identity_utils_accepts_real_brand_names():
    assert is_actionable_company_name("Tenaris") is True
    assert is_actionable_company_name("DomainTools") is True
    assert is_actionable_company_name("Expert Choice US LLC") is True

def test_company_identity_utils_rejects_wrapper_and_hiring_noise():
    assert is_non_actionable_company_name("Hiring") is True
    assert is_non_actionable_company_name("Careers") is True
    assert is_non_actionable_company_name("Remote") is True
    assert is_non_actionable_company_name("Vacantes") is True

def test_company_identity_utils_rejects_title_noise_as_company_name():
    assert is_non_actionable_company_name("Senior Backend Engineer") is True
    assert is_non_actionable_company_name("Remote Python Developer") is True
    assert is_non_actionable_company_name("Junior QA Tester") is True

def test_company_identity_utils_rejects_person_names_as_company_names():
    assert is_non_actionable_company_name("Juan Perez") is True
    assert is_non_actionable_company_name("María González") is True
    assert is_non_actionable_company_name("Carlos Rodriguez") is True

def test_company_identity_utils_rejects_ambiguous_company_patterns():
    assert is_non_actionable_company_name("Importante empresa del sector financiero") is True
    assert is_non_actionable_company_name("Leading company in tech") is True
    assert is_non_actionable_company_name("Fast growing company") is True
    assert is_non_actionable_company_name("Stealth startup") is True
