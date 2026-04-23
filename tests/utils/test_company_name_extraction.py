from oie.utils.company_name_extraction import extract_actionable_company_name


def test_extract_company_name_from_title_at_pattern():
    result = extract_actionable_company_name(
        company_display="unknown",
        title="Backend Engineer at Tenaris",
        snippet="",
        apply_url="",
    )
    assert result == "Tenaris"


def test_extract_company_name_rejects_generic_world_candidate():
    result = extract_actionable_company_name(
        company_display="World",
        title="Remote World is hiring Senior Python Engineer",
        snippet="",
        apply_url="",
    )
    assert result is None


def test_extract_company_name_rejects_confidential_company():
    result = extract_actionable_company_name(
        company_display="Empresa Confidencial",
        title="Senior Backend Engineer",
        snippet="",
        apply_url="",
    )
    assert result is None


def test_extract_company_name_does_not_infer_from_ats_domain_path():
    result = extract_actionable_company_name(
        company_display="unknown",
        title="Senior Backend Engineer",
        snippet="",
        apply_url="https://empresa-confidencial.gupy.io/jobs/12345",
    )
    assert result is None

def test_extract_company_name_does_not_infer_from_google_wrapper_url():
    result = extract_actionable_company_name(
        company_display="unknown",
        title="Senior Backend Engineer",
        snippet="",
        apply_url="https://www.google.com/about/careers/applications/jobs/results/12345",
    )
    assert result is None


def test_extract_company_name_does_not_return_role_from_ambiguous_title_chunks():
    result = extract_actionable_company_name(
        company_display="unknown",
        title="Senior Backend Engineer - Remote",
        snippet="",
        apply_url="",
    )
    assert result is None


def test_extract_company_name_from_title_pipe_when_only_one_side_is_company():
    result = extract_actionable_company_name(
        company_display="unknown",
        title="Senior Backend Engineer | Tenaris",
        snippet="",
        apply_url="",
    )
    assert result == "Tenaris"



def test_extract_company_name_from_clean_snippet_at_pattern():
    result = extract_actionable_company_name(
        company_display="unknown",
        title="Senior Backend Engineer",
        snippet="Join our engineering team at Tenaris building core platforms for the energy sector.",
        apply_url="",
    )
    assert result == "Tenaris"


def test_extract_company_name_does_not_infer_from_contaminated_snippet():
    result = extract_actionable_company_name(
        company_display="unknown",
        title="Senior Backend Engineer",
        snippet="Apply now via LinkedIn. Senior Backend Engineer at Retail Reach Co. Easy Apply.",
        apply_url="",
    )
    assert result is None

def test_extract_company_name_trims_snippet_noise_after_company_name():
    result = extract_actionable_company_name(
        company_display="unknown",
        title="Senior Backend Engineer",
        snippet="Join us at Retail Reach Co hiring product teams across LATAM.",
        apply_url="",
    )
    assert result == "Retail Reach Co"

