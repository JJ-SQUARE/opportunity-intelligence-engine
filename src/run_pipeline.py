from __future__ import annotations

import os
from typing import Any, Dict, List

import pandas as pd

from collectors.run_collectors import run_collectors as run_enabled_collectors

from pipeline.normalize import normalize_jobs
from pipeline.dedupe import dedupe_jobs
from pipeline.aggregate import aggregate_by_company

from scoring.signals import enrich_job_with_signals
from scoring.basic_score import basic_opportunity_score
from scoring.ai_company_classifier import classify_company_with_llm

from export.to_csv import export_jobs_csv
from export.to_company_csv import export_companies_csv
from export.to_leads_csv import export_leads_csv

from enrichment.router import enrich_company

from domain_resolution.google_serpapi import resolve_company_domain_serpapi, is_blocked_domain
from domain_resolution.cache import get_cached_domain, set_cached_domain

from sales_intel.classify import build_sales_and_competitive_lists
from export.to_sales_opportunities_csv import export_sales_opportunities_csv
from export.to_competitive_watchlist_csv import export_competitive_watchlist_csv

from utils.run_paths import build_run_dir, join_run_path
from utils.run_summary import write_run_summary


def company_signals(company_obj: Dict[str, Any]) -> Dict[str, Any]:
    jobs = company_obj.get("jobs", [])

    contractor = any(j.get("is_contractor") for j in jobs)

    remote = any(j.get("is_remote") for j in jobs) or any(
        "remote" in (j.get("location") or "").lower() for j in jobs
    )

    us_only = any(j.get("us_only") for j in jobs)
    nearshore = any(j.get("nearshore_friendly") for j in jobs) and not us_only

    urgency = sum(int(j.get("urgency_hits") or 0) for j in jobs) + sum(
        1 for j in jobs if j.get("many_openings_signal")
    )

    countries = [j.get("country") for j in jobs if j.get("country")]
    country_focus = max(set(countries), key=countries.count) if countries else None

    return {
        "contractor_signal": contractor,
        "remote_friendly_signal": remote,
        "us_only_signal": us_only,
        "nearshore_friendly_signal": nearshore,
        "urgency_signal": urgency,
        "country_focus": country_focus,
    }


def _norm_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    d = domain.strip().lower()
    if d.startswith("http://"):
        d = d[len("http://") :]
    if d.startswith("https://"):
        d = d[len("https://") :]
    d = d.replace("www.", "")
    d = d.split("/")[0]
    return d or None


def run(cfg: Dict[str, Any]) -> Dict[str, Any]:
    run_dir = build_run_dir(cfg)
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    jobs_csv = join_run_path(run_dir, "jobs_enriched.csv")
    companies_csv = join_run_path(run_dir, "companies_scored.csv")
    enrichment_input_csv = join_run_path(run_dir, "enrichment_input.csv")
    leads_csv = join_run_path(run_dir, "leads.csv")

    sales_opportunities_csv = join_run_path(run_dir, "sales_opportunities.csv")
    competitive_watchlist_csv = join_run_path(run_dir, "competitive_watchlist.csv")
    partners_path = join_run_path(run_dir, "partner_opportunities.csv")

    # ---------------------------------------------------------------------
    # 1) COLLECT (all enabled collectors, unified schema enforced upstream)
    # ---------------------------------------------------------------------
    jobs = run_enabled_collectors(cfg)  # <- centraliza todo por YAML

    # 2) Normalize + dedupe
    jobs = normalize_jobs(jobs)
    jobs = dedupe_jobs(jobs)

    # 3) Enrich job signals
    jobs = [enrich_job_with_signals(j) for j in jobs]

    export_jobs_csv(jobs, jobs_csv)

    # 4) Aggregate + score
    companies = aggregate_by_company(jobs)

    scored: List[Dict[str, Any]] = []
    for c in companies:
        c.update(company_signals(c))
        score = basic_opportunity_score(c) + min(c.get("urgency_signal", 0), 8)

        if c.get("contractor_signal"):
            score += 2
        if c.get("remote_friendly_signal") and not c.get("us_only_signal"):
            score += 2
        if c.get("nearshore_friendly_signal"):
            score += 3
        if c.get("us_only_signal"):
            score -= 3

        c["score"] = round(score, 2)
        scored.append(c)

    scored.sort(key=lambda x: float(x.get("score") or 0), reverse=True)

    # 5) LLM classification (optional)
    llm_cfg = cfg.get("llm", {}) or {}
    if llm_cfg.get("enabled", True):
        top_n = int(llm_cfg.get("top_n", 10))
        provider = llm_cfg.get("provider", "openai")
        model = llm_cfg.get("model", "gpt-4.1-mini")
        temperature = float(llm_cfg.get("temperature", 0.2))
        cache_path = llm_cfg.get("cache_path", "data/processed/company_ai_cache.json")

        for c in scored[:top_n]:
            ai = classify_company_with_llm(
                company=c.get("company", ""),
                context=c,
                provider=provider,
                model=model,
                temperature=temperature,
                cache_path=cache_path,
            )
            c["company_type_ai"] = ai.get("company_type")
            c["industry_ai"] = ai.get("industry")
            c["vendor_acceptance_probability_ai"] = ai.get("vendor_acceptance_probability")
            c["nearshore_friendly_ai"] = ai.get("nearshore_friendly")
            c["remote_friendly_ai"] = ai.get("remote_friendly")
            c["notes_ai"] = ai.get("notes")

    # 6) Domain resolution (top N)
    domain_cfg = cfg.get("domain_resolution", {}) or {}
    if bool(domain_cfg.get("enabled", True)):
        domain_top_n = int(domain_cfg.get("top_n", 50))

        for c in scored[:domain_top_n]:
            if c.get("resolved_domain"):
                continue

            domain = _norm_domain(c.get("domain_guess"))
            if domain and is_blocked_domain(domain):
                domain = None

            if not domain:
                cached = _norm_domain(get_cached_domain(c.get("company", "")))
                if cached and not is_blocked_domain(cached):
                    domain = cached
                else:
                    resolved = _norm_domain(resolve_company_domain_serpapi(c.get("company", "")))
                    if resolved and not is_blocked_domain(resolved):
                        domain = resolved
                        set_cached_domain(c.get("company", ""), domain)

            c["resolved_domain"] = domain

    out_companies = export_companies_csv(scored, companies_csv) or companies_csv

    # 7) enrichment_input.csv (debug/trace)
    rows = []
    for c in scored:
        rows.append(
            {
                "company": c.get("company"),
                "domain_guess": c.get("domain_guess"),
                "resolved_domain": c.get("resolved_domain"),
                "score": c.get("score"),
                "industry_ai": c.get("industry_ai"),
                "company_type_ai": c.get("company_type_ai"),
                "vendor_acceptance_probability_ai": c.get("vendor_acceptance_probability_ai"),
                "contractor_signal": c.get("contractor_signal"),
                "remote_friendly_signal": c.get("remote_friendly_signal"),
                "us_only_signal": c.get("us_only_signal"),
                "nearshore_friendly_signal": c.get("nearshore_friendly_signal"),
            }
        )
    pd.DataFrame(rows).to_csv(enrichment_input_csv, index=False)

    # 8) Enrichment (optional)
    enrichment_cfg = cfg.get("enrichment", {}) or {}
    all_leads: List[Dict[str, Any]] = []

    if enrichment_cfg.get("enabled", False):
        filters = enrichment_cfg.get("filters", {}) or {}
        limits = enrichment_cfg.get("limits", {}) or {}
        max_companies = int(limits.get("max_companies", 25))

        min_score = float(filters.get("min_score", 0))
        vendor_min = float(filters.get("vendor_prob_min", 0))
        require_not_us_only = bool(filters.get("require_not_us_only", False))

        eligible: List[Dict[str, Any]] = []
        for c in scored:
            score = float(c.get("score") or 0)
            vendor_prob_raw = c.get("vendor_acceptance_probability_ai")
            vendor_prob = float(vendor_prob_raw or 0)

            domain = _norm_domain(c.get("resolved_domain") or c.get("domain_guess"))
            if domain and is_blocked_domain(domain):
                domain = None

            if score < min_score:
                continue
            if vendor_prob < vendor_min:
                continue
            if require_not_us_only and c.get("us_only_signal"):
                continue

            if not domain:
                cached = _norm_domain(get_cached_domain(c.get("company", "")))
                if cached and not is_blocked_domain(cached):
                    domain = cached
                else:
                    resolved = _norm_domain(resolve_company_domain_serpapi(c.get("company", "")))
                    if resolved and not is_blocked_domain(resolved):
                        domain = resolved
                        set_cached_domain(c.get("company", ""), domain)

            c["resolved_domain"] = domain
            if not domain:
                continue

            eligible.append(c)

        eligible = eligible[:max_companies]
        print(f"Enrichment: eligible companies = {len(eligible)}")

        for c in eligible:
            leads = enrich_company(c, enrichment_cfg)
            all_leads.extend(leads)

        out_leads = export_leads_csv(all_leads, leads_csv)
        print(f"Saved leads to {out_leads}")
    else:
        out_leads = None

    # 9) Sales intel
    sales_intel_cfg = cfg.get("sales_intel", {}) or {}
    if sales_intel_cfg.get("enabled", True):
        end_clients, partners, competitive_list = build_sales_and_competitive_lists(scored, sales_intel_cfg)

        out_sales = export_sales_opportunities_csv(end_clients, sales_opportunities_csv)
        out_partners = export_sales_opportunities_csv(partners, partners_path)
        out_comp = export_competitive_watchlist_csv(competitive_list, competitive_watchlist_csv)

        print(f"Saved sales opportunities to {out_sales} ({len(end_clients)} rows)")
        print(f"Saved possible partners to {out_partners} ({len(partners)} rows)")
        print(f"Saved competitive watchlist to {out_comp} ({len(competitive_list)} rows)")
    else:
        out_sales, out_partners, out_comp = None, None, None
        end_clients, partners, competitive_list = [], [], []

    print(f"Run saved to: {run_dir}")

    summary_path = write_run_summary(
        run_dir=run_dir,
        jobs_count=len(jobs),
        companies_count=len(scored),
        end_clients=end_clients,
        partners=partners,
        competitive_list=competitive_list,
        leads_count=len(all_leads) if enrichment_cfg.get("enabled", False) else 0,
    )
    print(f"Run summary written to: {summary_path}")

    return {
        "jobs_count": len(jobs),
        "companies_count": len(scored),
        "jobs_csv": jobs_csv,
        "companies_csv": out_companies,
        "top_companies": scored[:10],
        "enrichment_input_csv": enrichment_input_csv,
        "leads_csv": leads_csv,
        "leads_count": len(all_leads) if enrichment_cfg.get("enabled", False) else 0,
        "sales_opportunities_csv": out_sales,
        "partner_opportunities_csv": out_partners or partners_path,
        "competitive_watchlist_csv": out_comp,
        "sales_opportunities_count": len(end_clients),
        "partners_opportunities_count": len(partners),
        "competitive_watchlist_count": len(competitive_list),
        "run_dir": run_dir,
    }