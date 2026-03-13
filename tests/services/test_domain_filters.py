from oie.utils.domain_filters import is_job_board_domain, normalize_domain


def test_normalize_domain_strips_scheme_and_www():
    assert normalize_domain("https://www.LinkedIn.com/jobs/view/123") == "linkedin.com"


def test_is_job_board_domain_exact():
    assert is_job_board_domain("linkedin.com") is True


def test_is_job_board_domain_subdomain():
    assert is_job_board_domain("mx.jooble.org") is True


def test_is_job_board_domain_false_for_corporate():
    assert is_job_board_domain("bairesdev.com") is False
