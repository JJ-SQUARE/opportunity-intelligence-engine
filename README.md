Opportunity Intelligence Engine

Opportunity Intelligence Engine is a configurable, AI-powered pipeline that transforms public hiring signals into structured, prioritized commercial intelligence.

It collects job postings from multiple sources, aggregates them by company, detects opportunity signals, classifies companies using LLMs, enriches them with verified leads, and maintains incremental master datasets without duplicates.

The system converts job market activity into actionable sales intelligence.

⸻

Overview

Public job postings contain valuable signals:
	•	Companies hiring multiple technical roles
	•	Contract-based positions
	•	Remote or nearshore-friendly policies
	•	Urgent hiring needs
	•	Modern tech stack adoption

However, this information is scattered and unstructured.

Opportunity Intelligence Engine transforms that noise into:
	•	Scored company opportunities
	•	AI-based vendor acceptance probability
	•	Real contact leads
	•	Sales segmentation
	•	Historical master datasets

⸻

Core Capabilities

1. Multi-Source Job Collection

Supports configurable collectors:
	•	Google Jobs (via SerpAPI)
	•	LinkedIn (via SerpAPI)
	•	Indeed
	•	ATS platforms (configurable)
	•	Career pages

Collectors are controlled via YAML configuration.

⸻

2. Job Normalization and Deduplication

Pipeline:

collect → normalize → dedupe → enrich signals

Standardizes:
	•	company
	•	title
	•	location
	•	country
	•	job_url
	•	apply_url
	•	source
	•	contractor flags
	•	remote flags
	•	urgency indicators

Deduplication strategy:
	•	Primary: job_url
	•	Fallback: company + title + source

⸻

3. Company Aggregation

Jobs are aggregated by company to compute:
	•	total_openings
	•	contractor_signal
	•	remote_friendly_signal
	•	nearshore_friendly_signal
	•	urgency_signal
	•	us_only_signal
	•	country_focus

⸻

4. Opportunity Scoring

Each company receives a composite score based on:
	•	Contract roles
	•	Remote flexibility
	•	Nearshore friendliness
	•	Hiring urgency
	•	US-only penalties

Companies are ranked by score to prioritize outreach.

⸻

5. AI Company Classification

Using OpenAI (configurable model), the system classifies:
	•	company_type_ai (consulting, product_company, staffing_agency, marketplace)
	•	industry_ai
	•	vendor_acceptance_probability_ai
	•	nearshore_friendly_ai
	•	remote_friendly_ai
	•	notes_ai (explanation of reasoning)

Results are cached to control API costs.

⸻

6. Real Domain Resolution

Job boards often mask the real hiring company.

The system resolves the true company domain using:
	1.	Apply/job URLs
	2.	Local cache
	3.	SerpAPI (configurable mode: serpapi or cache_only)
	4.	Blocked-domain filtering (job boards excluded)

Resolved domains are stored in:

resolved_domain

This ensures enrichment targets the real company, not the publisher.

⸻

7. Lead Enrichment (Hunter Integration)

Eligible companies are enriched via Hunter Domain Search API.

Filters include:
	•	Minimum score
	•	Vendor probability threshold
	•	US-only exclusion
	•	Max companies per run

Extracted fields:
	•	email
	•	first_name
	•	last_name
	•	position
	•	department
	•	seniority
	•	confidence
	•	linkedin

Results are stored in:
	•	leads.csv (per run)
	•	master_leads.csv (incremental)

⸻

8. Sales Intelligence Segmentation

Companies are automatically classified into:
	•	Sales Opportunities (End Clients)
	•	Partner Opportunities
	•	Competitive Watchlist

Based on:
	•	Company type
	•	Vendor probability
	•	Score thresholds
	•	Segmentation configuration

⸻

9. Incremental Master Data Store

The engine maintains deduplicated master files:
	•	master_jobs.csv
	•	master_companies.csv
	•	master_leads.csv

Features:
	•	Strong deduplication keys
	•	Append-only logic
	•	Corruption protection
	•	Historical persistence

⸻

Project Structure

src/
  collectors/
  pipeline/
  scoring/
  enrichment/
  domain_resolution/
  sales_intel/
  export/
  utils/

Output directories:

runs/YYYY-MM-DD_HHMM/
spreadsheets/
data/processed/


⸻

Configuration

The system is fully driven by YAML configuration.

Key sections:
	•	sources
	•	llm
	•	domain_resolution
	•	enrichment
	•	sales_intel
	•	outputs

Example:

domain_resolution:
  enabled: true
  mode: serpapi
  top_n: 50


⸻

Technologies Used
	•	Python 3.12
	•	Pandas
	•	Requests
	•	SerpAPI
	•	Hunter.io API
	•	OpenAI (GPT models)

⸻

Execution Flow
	1.	Collect jobs
	2.	Normalize and dedupe
	3.	Aggregate by company
	4.	Score companies
	5.	AI classify top companies
	6.	Resolve real domains
	7.	Enrich eligible companies with leads
	8.	Segment into sales categories
	9.	Append results to master spreadsheets

⸻

Example Outputs

Per run:
	•	jobs_enriched.csv
	•	companies_scored.csv
	•	enrichment_input.csv
	•	leads.csv
	•	sales_opportunities.csv
	•	partner_opportunities.csv
	•	competitive_watchlist.csv
	•	RUN_SUMMARY.txt

Historical:
	•	master_jobs.csv
	•	master_companies.csv
	•	master_leads.csv

⸻

Roadmap

Planned enhancements include:
	•	Improved end-client detection from job boards
	•	Advanced vendor probability modeling
	•	Multi-provider enrichment (Apollo, Clearbit)
	•	Multi-dimensional scoring
	•	Dashboard interface
	•	CRM integration (HubSpot / Salesforce)
	•	Feedback loop from sales outcomes
	•	Automated pitch generation per company

⸻

Purpose

This engine converts hiring signals into structured commercial intelligence.

It is designed for:
	•	Nearshore software vendors
	•	Consulting firms
	•	Sales intelligence teams
	•	Strategic partnership development

It bridges hiring data and revenue opportunity.
