from oie.services.domain_confidence_service import DomainConfidenceService


def test_score_candidate_high_confidence_brand_domain():
    svc = DomainConfidenceService()

    result = svc.score_candidate(
        company_name="BairesDev",
        domain="bairesdev.com",
        source="serpapi_fallback",
        serp_rank=1,
        title="BairesDev - Official Website",
        snippet="BairesDev builds software teams",
    )

    assert result["score"] >= 0.80
    assert result["review_required"] is False
    assert result["validation_status"] == "accepted"


def test_score_candidate_low_confidence_generic_name_with_gov_domain():
    svc = DomainConfidenceService()

    result = svc.score_candidate(
        company_name="Join ready",
        domain="ready.gov",
        source="serpapi_fallback",
        serp_rank=1,
        title="READY.gov official site",
        snippet="Disaster preparedness information",
    )

    assert result["score"] < 0.80
    assert result["validation_status"] in {"review", "rejected"}


def test_pick_best_candidate_prefers_brand_match_over_weaker_match():
    svc = DomainConfidenceService()

    best = svc.pick_best_candidate(
        company_name="Tekton Labs",
        candidates=[
            {
                "domain": "recruit.net",
                "source": "apply_url",
                "serp_rank": None,
                "title": "",
                "snippet": "",
            },
            {
                "domain": "tektonlabs.com",
                "source": "serpapi_fallback",
                "serp_rank": 1,
                "title": "Tekton Labs | Software Development",
                "snippet": "Official Tekton Labs website",
            },
        ],
    )

    assert best is not None
    assert best["domain"] == "tektonlabs.com"
    assert best["score"] >= 0.70


def test_score_candidate_accepts_legit_brand_domain_with_extra_wording():
    svc = DomainConfidenceService()

    result = svc.score_candidate(
        company_name="Congelados Polar",
        domain="polardistribuciones.com.ar",
        source="serpapi_fallback",
        serp_rank=1,
        title="Polar Distribuciones",
        snippet="Distribución y comercialización",
    )

    assert result["validation_status"] in {"accepted", "review"}
    assert result["score"] >= 0.40


def test_score_candidate_rejects_known_job_board_brand_domain():
    svc = DomainConfidenceService()

    result = svc.score_candidate(
        company_name="HIRELINE",
        domain="hireline.com",
        source="serpapi_fallback",
        serp_rank=1,
        title="Hireline México - Empleos de tecnología",
        snippet="Bolsa de trabajo para vacantes tech",
    )

    assert result["validation_status"] == "rejected"
    assert result["score"] < svc.review_threshold


def test_score_candidate_forces_review_for_suspicious_beta_subdomain():
    svc = DomainConfidenceService()

    result = svc.score_candidate(
        company_name="Rimutee",
        domain="beta.rimutee.com",
        source="serpapi_fallback",
        serp_rank=1,
        title="Rimutee - Official Website",
        snippet="Remote talent platform",
    )

    assert result["validation_status"] == "review"
    assert result["review_required"] is True

def test_score_candidate_does_not_auto_accept_ambiguous_short_single_token_brand():
    svc = DomainConfidenceService()

    result = svc.score_candidate(
        company_name="NOUS",
        domain="nous.example.com",
        source="serpapi_fallback",
        serp_rank=1,
        title="NOUS platform",
        snippet="Innovation platform",
    )

    assert result["validation_status"] != "accepted"
    assert result["review_required"] is True



def test_score_candidate_forces_review_for_homonym_like_serp_result_without_brand_support():
    svc = DomainConfidenceService()

    result = svc.score_candidate(
        company_name="NOUS",
        domain="nous.example.com",
        source="serpapi_fallback",
        serp_rank=1,
        title="Innovation platform",
        snippet="AI marketplace and jobs platform",
    )

    assert result["validation_status"] == "review"
    assert result["review_required"] is True


def test_score_candidate_rejects_unrelated_jobish_text_even_with_partial_brand_hit():
    svc = DomainConfidenceService()

    result = svc.score_candidate(
        company_name="Rimutee",
        domain="rimutee.example.com",
        source="serpapi_fallback",
        serp_rank=1,
        title="Jobs platform",
        snippet="Vacantes, empleos y talent platform",
    )

    assert result["validation_status"] in {"review", "rejected"}
    assert result["score"] < 0.80
