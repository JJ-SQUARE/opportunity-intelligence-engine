from oie.persistence.repositories import JobRepository, LeadRepository


def test_job_fingerprint_is_stable_across_runs_when_job_url_exists():
    repo = JobRepository("data/test_unused.db")
    job = {
        "title": "Backend Engineer",
        "company": "Acme Inc.",
        "location": "Remote",
        "job_url": "https://acme.com/jobs/1",
        "apply_url": "https://acme.com/apply/1",
        "description": "Python role",
    }

    fp_a = repo._build_job_fingerprint(job)
    fp_b = repo._build_job_fingerprint(job)

    assert fp_a == fp_b


def test_job_key_changes_by_run_but_keeps_same_fingerprint():
    repo = JobRepository("data/test_unused.db")
    job = {
        "title": "Backend Engineer",
        "company": "Acme Inc.",
        "location": "Remote",
        "job_url": "https://acme.com/jobs/1",
        "apply_url": "https://acme.com/apply/1",
        "description": "Python role",
    }

    fp_a = repo._build_job_fingerprint(job)
    fp_b = repo._build_job_fingerprint(job)
    key_a = repo._build_job_key(job, "run_001")
    key_b = repo._build_job_key(job, "run_002")

    assert fp_a == fp_b
    assert key_a != key_b


def test_lead_fingerprint_is_stable_across_runs_when_email_exists():
    repo = LeadRepository("data/test_unused.db")
    lead = {
        "company_key": "cmp_a",
        "contact_name": "Jane Doe",
        "contact_title": "CTO",
        "email": "jane@acme.com",
        "linkedin_url": "https://linkedin.com/in/jane",
    }

    fp_a = repo._build_lead_fingerprint(lead)
    fp_b = repo._build_lead_fingerprint(lead)

    assert fp_a == fp_b


def test_lead_key_changes_by_run_but_keeps_same_fingerprint():
    repo = LeadRepository("data/test_unused.db")
    lead = {
        "company_key": "cmp_a",
        "contact_name": "Jane Doe",
        "contact_title": "CTO",
        "email": "jane@acme.com",
        "linkedin_url": "https://linkedin.com/in/jane",
    }

    fp_a = repo._build_lead_fingerprint(lead)
    fp_b = repo._build_lead_fingerprint(lead)
    key_a = repo._build_lead_key(lead, "run_001")
    key_b = repo._build_lead_key(lead, "run_002")

    assert fp_a == fp_b
    assert key_a != key_b
