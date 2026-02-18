from dotenv import load_dotenv

from config_loader import load_config
from run_pipeline import run


def main():
    load_dotenv()
    cfg = load_config()
    result = run(cfg)

    print(f"Saved {result['jobs_count']} jobs -> {result['jobs_csv']}")
    print(f"Saved {result['companies_count']} companies -> {result['companies_csv']}")

    print("\nTop Opportunities:")
    for c in result["top_companies"]:
        print(
            f"{c['company']} | Openings: {c['total_openings']} | "
            f"Score: {c['score']} | Industry: {c.get('industry_ai')}"
        )


if __name__ == "__main__":
    main()