from oie.utils.domain_filters import is_job_board_domain, normalize_domain


def test_domain_filters_normalize_domain():
    assert normalize_domain("https://www.Example.com/hello") == "example.com"


def test_domain_filters_detects_ats_and_job_boards():
    assert is_job_board_domain("jobgether.com") is True
    assert is_job_board_domain("boards.greenhouse.io") is True
    assert is_job_board_domain("empresa-confidencial.gupy.io") is True
    assert is_job_board_domain("acme.com") is False

def test_domain_filters_detects_wrappers_and_shorteners_as_blocked_domains():
    assert is_job_board_domain("google.com") is True
    assert is_job_board_domain("www.google.com") is True
    assert is_job_board_domain("lnkd.in") is True
    assert is_job_board_domain("bit.ly") is True



def test_domain_filters_detects_more_job_aggregators():
    assert is_job_board_domain("careerjet.com") is True
    assert is_job_board_domain("wellfound.com") is True
    assert is_job_board_domain("buscojobs.com") is True
