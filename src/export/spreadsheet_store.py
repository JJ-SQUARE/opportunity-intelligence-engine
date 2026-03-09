from __future__ import annotations

import os
from typing import Optional
import pandas as pd


def _safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        # pandas>=1.3
        return pd.read_csv(path, on_bad_lines="skip")
    except TypeError:
        # compat si on_bad_lines no existe
        try:
            return pd.read_csv(path, error_bad_lines=False, warn_bad_lines=True)  # deprecated en pandas nuevos
        except Exception:
            return pd.DataFrame()
    except Exception:
        # ÚLTIMO recurso: no te cargues el master
        return pd.DataFrame()


def _write_csv(df: pd.DataFrame, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    return path


def _col_or_empty(df: pd.DataFrame, col: str) -> pd.Series:
    """Return df[col] if exists; otherwise an empty-string Series aligned to df.index."""
    if col in df.columns:
        return df[col]
    return pd.Series([""] * len(df), index=df.index)


def append_master_jobs(spreadsheets_dir: str, run_jobs_csv: Optional[str]) -> str:
    master_path = os.path.join(spreadsheets_dir, "master_jobs.csv")
    master = _safe_read_csv(master_path)

    if not run_jobs_csv or not os.path.exists(run_jobs_csv):
        return _write_csv(master, master_path)

    cur = _safe_read_csv(run_jobs_csv)

    if cur.empty:
        return _write_csv(master, master_path)

    # Dedupe key: prefer job_url; fallback to (company,title,source)
    # Dedupe key: prefer job_url; fallback to (company,title,source)
    has_url = "job_url" in cur.columns

    if has_url:
        url_key = cur["job_url"].fillna("").astype(str).str.strip().str.lower()

        fallback = (
                _col_or_empty(cur, "company").fillna("").astype(str).str.strip().str.lower()
                + "|" + _col_or_empty(cur, "title").fillna("").astype(str).str.strip().str.lower()
                + "|" + _col_or_empty(cur, "source").fillna("").astype(str).str.strip().str.lower()
        )

        # Si job_url está vacío → usar fallback
        cur["_dedupe_key"] = url_key.where(url_key != "", fallback)

    else:
        cur["_dedupe_key"] = (
                _col_or_empty(cur, "company").fillna("").astype(str).str.strip().str.lower()
                + "|" + _col_or_empty(cur, "title").fillna("").astype(str).str.strip().str.lower()
                + "|" + _col_or_empty(cur, "source").fillna("").astype(str).str.strip().str.lower()
        )

    if not master.empty:
        has_url_m = "job_url" in master.columns

        if has_url_m:
            url_key_m = master["job_url"].fillna("").astype(str).str.strip().str.lower()
            fallback_m = (
                    _col_or_empty(master, "company").fillna("").astype(str).str.strip().str.lower()
                    + "|" + _col_or_empty(master, "title").fillna("").astype(str).str.strip().str.lower()
                    + "|" + _col_or_empty(master, "source").fillna("").astype(str).str.strip().str.lower()
            )
            master["_dedupe_key"] = url_key_m.where(url_key_m != "", fallback_m)
        else:
            master["_dedupe_key"] = (
                    _col_or_empty(master, "company").fillna("").astype(str).str.strip().str.lower()
                    + "|" + _col_or_empty(master, "title").fillna("").astype(str).str.strip().str.lower()
                    + "|" + _col_or_empty(master, "source").fillna("").astype(str).str.strip().str.lower()
            )

    out = pd.concat([master, cur], ignore_index=True)
    out = out.drop_duplicates(subset=["_dedupe_key"], keep="first").drop(columns=["_dedupe_key"], errors="ignore")
    return _write_csv(out, master_path)


def append_master_companies(spreadsheets_dir: str, run_companies_csv: Optional[str]) -> str:
    master_path = os.path.join(spreadsheets_dir, "master_companies.csv")
    master = _safe_read_csv(master_path)

    if os.path.exists(master_path) and master.empty and os.path.getsize(master_path) > 0:
        print(f"[spreadsheets][WARN] Could not parse {master_path}. Skipping overwrite to avoid data loss.")
        return master_path

    if not run_companies_csv or not os.path.exists(run_companies_csv):
        return _write_csv(master, master_path)

    cur = _safe_read_csv(run_companies_csv)

    if cur.empty:
        return _write_csv(master, master_path)

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

    if os.path.exists(master_path) and master.empty and os.path.getsize(master_path) > 0:
        print(f"[spreadsheets][WARN] Could not parse {master_path}. Skipping overwrite to avoid data loss.")
        return master_path

    if not run_leads_csv or not os.path.exists(run_leads_csv):
        return _write_csv(master, master_path)

    cur = _safe_read_csv(run_leads_csv)

    # Si el archivo existe pero está vacío / sin header, no hagas nada
    if cur.empty:
        return _write_csv(master, master_path)

    # Dedupe by email|domain (safer than email alone)
    if "email" in cur.columns:
        email = cur["email"].fillna("").astype(str).str.strip().str.lower()
        domain = _col_or_empty(cur, "domain").fillna("").astype(str).str.strip().str.lower()
        cur["_dedupe_key"] = email + "|" + domain
    else:
        cur["_dedupe_key"] = ""

    if not master.empty and "email" in master.columns:
        email_m = master["email"].fillna("").astype(str).str.strip().str.lower()
        domain_m = _col_or_empty(master, "domain").fillna("").astype(str).str.strip().str.lower()
        master["_dedupe_key"] = email_m + "|" + domain_m

    out = pd.concat([master, cur], ignore_index=True)
    out = out.drop_duplicates(subset=["_dedupe_key"], keep="first").drop(columns=["_dedupe_key"], errors="ignore")
    return _write_csv(out, master_path)


def append_run_to_spreadsheets(spreadsheets_dir: str, jobs_csv: str | None, companies_csv: str | None, leads_csv: str | None) -> dict:
    return {
        "master_jobs": append_master_jobs(spreadsheets_dir, jobs_csv),
        "master_companies": append_master_companies(spreadsheets_dir, companies_csv),
        "master_leads": append_master_leads(spreadsheets_dir, leads_csv),
    }