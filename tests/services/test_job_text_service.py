from oie.services.job_text_service import (
    build_job_summary,
    description_looks_contaminated,
    extract_budget,
    extract_techs,
    safe_job_description,
)


def test_job_text_service_hides_contaminated_serp_snippet():
    job = {
        "title": "Distributed Systems Engineer - DomainTools",
        "source": "linkedin_serpapi",
        "description": "Desarrollador Full Stack - Remoto Colombia. NTT DATA Europe & Latam. Colombia Hace 6 días. Platform Support Engineer ...",
    }

    assert description_looks_contaminated(job) is True
    assert safe_job_description(job) == ""

    summary = build_job_summary(job)
    assert "Descripción no confiable" in summary
    assert "NTT DATA Europe" not in summary
    assert "Platform Support Engineer" not in summary


def test_job_text_service_extracts_budget_and_tech_stack_from_safe_description():
    description = "Senior backend role using Python, AWS and Docker. Budget USD $5,000 - USD $6,000."
    job = {
        "title": "Senior Backend Engineer",
        "source": "greenhouse",
        "description": description,
        "is_remote": True,
    }

    assert safe_job_description(job) == description
    assert extract_budget(description) == "USD $5,000 - USD $6,000"
    assert "python" in extract_techs(description)
    assert "aws" in extract_techs(description)
    assert "docker" in extract_techs(description)
