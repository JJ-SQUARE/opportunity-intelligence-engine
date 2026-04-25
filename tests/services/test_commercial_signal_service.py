from oie.services.commercial_signal_service import CommercialSignalService


def test_commercial_signal_service_deprioritizes_known_vendor_names_even_if_unknown():
    service = CommercialSignalService()

    row = service.finalize_row(
        {
            "company_display": "Softtek",
            "company_type_ai": "unknown",
            "opportunity_score": 65,
            "score_pain_urgency": 20,
            "score_role_seniority_mix": 7,
            "total_openings": 3,
            "domain_validation_status": "accepted",
            "resolved_domain": "jobs.softtek.com",
        }
    )

    assert row["commercially_actionable"] is False
    assert row["commercial_bucket"] == "competitor_watchlist"
    assert row["outreach_status"] == "deprioritized_competitor"
    assert row["commercial_priority_score"] <= 35


def test_commercial_signal_service_does_not_treat_unknown_pain_alone_as_real_icp():
    service = CommercialSignalService()

    row = service.finalize_row(
        {
            "company_display": "Unknown Tech Co",
            "company_type_ai": "unknown",
            "opportunity_score": 45,
            "score_icp_fit": 5,
            "score_pain_urgency": 12,
            "score_role_seniority_mix": 7,
            "total_openings": 2,
            "domain_validation_status": "accepted",
            "resolved_domain": "unknowntech.example",
        }
    )

    assert row["commercially_actionable"] is False
    assert row["commercial_bucket"] == "low_fit_noise"

def test_commercial_signal_service_allows_investigable_unknown_with_real_domain_and_job_signal():
    service = CommercialSignalService()

    row = service.finalize_row(
        {
            "company_display": "Varicent Like Co",
            "company_type_ai": "unknown",
            "opportunity_score": 54,
            "score_icp_fit": 15,
            "score_pain_urgency": 10,
            "score_role_seniority_mix": 5,
            "total_openings": 1,
            "domain_validation_status": "accepted",
            "resolved_domain": "varicent-like.com",
            "linkedin_company_url": "https://linkedin.com/company/varicent-like",
        }
    )

    assert row["commercially_actionable"] is True
    assert row["commercial_bucket"] == "partner_candidate"
    assert row["icp_bucket"] == "possible_icp"
    assert row["commercial_priority_score"] > 0


def test_commercial_signal_service_rejects_investigable_unknown_with_reserved_example_domain():
    service = CommercialSignalService()

    row = service.finalize_row(
        {
            "company_display": "Unknown Tech Co",
            "company_type_ai": "unknown",
            "opportunity_score": 45,
            "score_icp_fit": 5,
            "score_pain_urgency": 12,
            "score_role_seniority_mix": 7,
            "total_openings": 2,
            "domain_validation_status": "accepted",
            "resolved_domain": "unknowntech.example",
        }
    )

    assert row["commercially_actionable"] is False
    assert row["commercial_bucket"] == "low_fit_noise"
    assert row["company_domain_usable"] is False

def test_commercial_signal_service_does_not_treat_company_linkedin_only_as_real_reachability():
    service = CommercialSignalService()

    row = service.finalize_row(
        {
            "company_display": "Low ICP End Client",
            "company_type_ai": "end_client",
            "opportunity_score": 20,
            "score_icp_fit": 5,
            "score_pain_urgency": 5,
            "total_openings": 1,
            "domain_validation_status": "accepted",
            "resolved_domain": "lowicp.example.com",
            "linkedin_company_url": "https://linkedin.com/company/lowicp",
        }
    )

    assert row["reachability_ready"] == 0
    assert row["real_reachability_ready"] == 0
    assert row["soft_reachability_ready"] == 1
    assert row["commercially_actionable"] is False
    assert row["commercial_priority_score"] == 0


def test_commercial_signal_service_allows_end_client_with_real_contact_reachability():
    service = CommercialSignalService()

    row = service.finalize_row(
        {
            "company_display": "Reachable Product Co",
            "company_type_ai": "end_client",
            "opportunity_score": 42,
            "score_icp_fit": 8,
            "score_pain_urgency": 8,
            "total_openings": 1,
            "domain_validation_status": "accepted",
            "resolved_domain": "reachableproduct.com",
            "best_contact_email": "cto@reachableproduct.com",
        }
    )

    assert row["reachability_ready"] == 1
    assert row["real_reachability_ready"] == 1
    assert row["commercially_actionable"] is True
    assert row["commercial_priority_score"] > 0
