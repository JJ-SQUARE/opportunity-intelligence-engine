from oie.utils.company_name_extraction import extract_actionable_company_name


def test_keeps_actionable_company_display():
    result = extract_actionable_company_name(
        company_display="Tenaris",
        title="Senior Engineer",
        snippet="Apply now",
        apply_url="https://jobgether.com/offer/123",
    )
    assert result == "Tenaris"


def test_extracts_company_name_from_title_when_display_is_confidential():
    result = extract_actionable_company_name(
        company_display="Confidencial",
        title="Backend Engineer at Tenaris",
        snippet="Remote role",
        apply_url="https://jobgether.com/offer/123",
    )
    assert result == "Tenaris"


def test_returns_none_for_non_actionable_company_name():
    result = extract_actionable_company_name(
        company_display="Confidencial",
        title="Backend Engineer",
        snippet="Great opportunity",
        apply_url="https://jobgether.com/offer/123",
    )
    assert result is None
