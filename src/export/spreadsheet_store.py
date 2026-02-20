from __future__ import annotations

import os
from typing import Optional
import pandas as pd


def _safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _write_csv(df: pd.DataFrame, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    return path


def append_master_jobs(spreadsheets_dir: str, run_jobs_csv: Optional[str]) -> str:
    master_path = os.path.join(spreadsheets_dir, "master_jobs.csv")
    master = _safe_read_csv(master_path)

    if not run_jobs_csv or not os.path.exists(run_jobs_csv):
        return _write_csv(master, master_path)

    cur = pd.read_csv(run_jobs_csv)

    # Dedupe key: prefer job_url; fallback to (company,title,source)
    if "job_url" in cur.columns:
        cur["_dedupe_key"] = cur["job_url"].fillna("").astype(str).str.strip().str.lower()
    else:
        cur["_dedupe_key"] = (
            cur.get("company", "").astype(str).str.lower().fillna("")
            + "|" + cur.get("title", "").astype(str).str.lower().fillna("")
            + "|" + cur.get("source", "").astype(str).str.lower().fillna("")
        )

    if not master.empty:
        if "job_url" in master.columns:
            master["_dedupe_key"] = master["job_url"].fillna("").astype(str).str.strip().str.lower()
        else:
            master["_dedupe_key"] = (
                master.get("company", "").astype(str).str.lower().fillna("")
                + "|" + master.get("title", "").astype(str).str.lower().fillna("")
                + "|" + master.get("source", "").astype(str).str.lower().fillna("")
            )

    out = pd.concat([master, cur], ignore_index=True)
    out = out.drop_duplicates(subset=["_dedupe_key"], keep="first").drop(columns=["_dedupe_key"], errors="ignore")
    return _write_csv(out, master_path)


def append_master_companies(spreadsheets_dir: str, run_companies_csv: Optional[str]) -> str:
    master_path = os.path.join(spreadsheets_dir, "master_companies.csv")
    master = _safe_read_csv(master_path)

    if not run_companies_csv or not os.path.exists(run_companies_csv):
        return _write_csv(master, master_path)

    cur = pd.read_csv(run_companies_csv)

    if "company" in cur.columns:
        cur["_dedupe_key"] = cur["company"].fillna("").astype(str).str.strip().str.lower()
    else:
        cur["_dedupe_key"] = ""

    if not master.empty and "company" in master.columns:
        master["_dedupe_key"] = master["company"].fillna("").astype(str).str.strip().str.lower()

    out = pd.concat([master, cur], ignore_index=True)
    out = out.drop_duplicates(subset=["_dedupe_key"], keep="first").drop(columns=["_dedupe_key"], errors="ignore")
    return _write_csv(out, master_path)


def append_master_leads(spreadsheets_dir: str, run_leads_csv: Optional[str]) -> str:
    master_path = os.path.join(spreadsheets_dir, "master_leads.csv")
    master = _safe_read_csv(master_path)

    if not run_leads_csv or not os.path.exists(run_leads_csv):
        return _write_csv(master, master_path)

    cur = pd.read_csv(run_leads_csv)

    # Dedupe by email
    if "email" in cur.columns:
        cur["_dedupe_key"] = cur["email"].fillna("").astype(str).str.strip().str.lower()
    else:
        cur["_dedupe_key"] = ""

    if not master.empty and "email" in master.columns:
        master["_dedupe_key"] = master["email"].fillna("").astype(str).str.strip().str.lower()

    out = pd.concat([master, cur], ignore_index=True)
    out = out.drop_duplicates(subset=["_dedupe_key"], keep="first").drop(columns=["_dedupe_key"], errors="ignore")
    return _write_csv(out, master_path)


def append_run_to_spreadsheets(spreadsheets_dir: str, jobs_csv: str | None, companies_csv: str | None, leads_csv: str | None) -> dict:
    return {
        "master_jobs": append_master_jobs(spreadsheets_dir, jobs_csv),
        "master_companies": append_master_companies(spreadsheets_dir, companies_csv),
        "master_leads": append_master_leads(spreadsheets_dir, leads_csv),
    }