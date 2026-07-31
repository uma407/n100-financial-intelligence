from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"

CAPITAL_FILE = OUTPUT_DIR / "capital_allocation.csv"
PATTERN_DISTRIBUTION_FILE = OUTPUT_DIR / "pattern_distribution.csv"
PATTERN_CHANGES_FILE = OUTPUT_DIR / "pattern_changes.csv"
CASHFLOW_INTELLIGENCE_FILE = OUTPUT_DIR / "cashflow_intelligence.xlsx"


def generate_reports():
    capital = pd.read_csv(CAPITAL_FILE)

    latest = (
        capital.sort_values("year")
        .groupby("company_id")
        .tail(1)
    )

    distribution = (
        latest["pattern_label"]
        .value_counts()
        .reset_index()
    )

    distribution.columns = [
        "pattern_label",
        "company_count",
    ]

    distribution.to_csv(
        PATTERN_DISTRIBUTION_FILE,
        index=False,
    )

    changes = []

    for company, group in capital.groupby("company_id"):
        group = group.sort_values("year")

        patterns = group["pattern_label"].tolist()
        years = group["year"].tolist()

        for i in range(1, len(patterns)):
            if patterns[i] != patterns[i - 1]:
                changes.append(
                    {
                        "company_id": company,
                        "previous_year": years[i - 1],
                        "previous_pattern": patterns[i - 1],
                        "current_year": years[i],
                        "current_pattern": patterns[i],
                    }
                )

    changes_df = pd.DataFrame(
        changes,
        columns=[
            "company_id",
            "previous_year",
            "previous_pattern",
            "current_year",
            "current_pattern",
        ],
    )

    changes_df.to_csv(
        PATTERN_CHANGES_FILE,
        index=False,
    )

    print("Day 32 reports completed")
    print("\nPattern Distribution:")
    print(distribution)

    print("\nPattern Changes:")
    print(changes_df.head(20))

    print("\nCreated:", PATTERN_DISTRIBUTION_FILE)
    print("Created:", PATTERN_CHANGES_FILE)


def update_cashflow_intelligence():
    intelligence = pd.read_excel(
        CASHFLOW_INTELLIGENCE_FILE
    )

    capital = pd.read_csv(CAPITAL_FILE)

    latest = (
        capital.sort_values("year")
        .groupby("company_id")
        .tail(1)[["company_id", "pattern_label"]]
    )

    intelligence = intelligence.drop(
        columns=["capital_allocation_label"],
        errors="ignore",
    )

    intelligence = intelligence.merge(
        latest,
        on="company_id",
        how="left",
    )

    intelligence.rename(
        columns={
            "pattern_label": "capital_allocation_label"
        },
        inplace=True,
    )

    intelligence.to_excel(
        CASHFLOW_INTELLIGENCE_FILE,
        index=False,
    )

    print("\nCashflow intelligence updated")
    print("Rows:", len(intelligence))
    print(
        "Companies:",
        intelligence["company_id"].nunique(),
    )


if __name__ == "__main__":
    generate_reports()
    update_cashflow_intelligence()