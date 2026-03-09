from __future__ import annotations

from oie.orchestration.run_context import RunContext
from oie.services.master_data_service import MasterDataService
from oie.services.master_dedup_service import MasterDedupService


def test_master_dedup_service_detects_duplicate_jobs_against_master(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    master_service = MasterDataService(ctx)
    dedup_service = MasterDedupService(ctx)

    master_service.append_jobs(
        [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "job_url": "https://acme.com/jobs/1",
                "apply_url": "",
                "description": "Python role",
                "source": "google_jobs",
                "detected_at": "2026-03-09",
            }
        ]
    )

    unique_jobs, duplicates = dedup_service.dedupe_jobs_against_master(
        [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "job_url": "https://acme.com/jobs/1",
                "apply_url": "",
                "description": "Python role",
                "source": "linkedin_jobs",
                "detected_at": "2026-03-10",
            },
            {
                "title": "Data Engineer",
                "company": "Beta",
                "location": "Remote",
                "job_url": "https://beta.com/jobs/2",
                "apply_url": "",
                "description": "Data role",
                "source": "google_jobs",
                "detected_at": "2026-03-10",
            },
        ]
    )

    assert len(unique_jobs) == 1
    assert len(duplicates) == 1
    assert unique_jobs[0]["title"] == "Data Engineer"


def test_master_dedup_service_detects_duplicate_leads_against_master(tmp_path):
    ctx = RunContext.create(
        config={"masters": {"path": str(tmp_path / "masters")}},
        flags={},
    )
    master_service = MasterDataService(ctx)
    dedup_service = MasterDedupService(ctx)

    master_service.append_leads(
        [
            {
                "company_key": "cmp_acme",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "jane@acme.com",
                "linkedin_url": "",
            }
        ]
    )

    unique_leads, duplicates = dedup_service.dedupe_leads_against_master(
        [
            {
                "company_key": "cmp_acme",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "jane@acme.com",
                "linkedin_url": "",
            },
            {
                "company_key": "cmp_beta",
                "contact_name": "John Roe",
                "contact_title": "VP Engineering",
                "email": "john@beta.com",
                "linkedin_url": "",
            },
        ]
    )

    assert len(unique_leads) == 1
    assert len(duplicates) == 1
    assert unique_leads[0]["email"] == "john@beta.com"
