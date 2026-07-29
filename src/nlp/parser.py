import re
import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "analysis.xlsx"
DATABASE_FILE = PROJECT_ROOT / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

PARSED_FILE = OUTPUT_DIR / "analysis_parsed.csv"
FAILURE_FILE = OUTPUT_DIR / "parse_failures.csv"
VALIDATION_FILE = OUTPUT_DIR / "analysis_cagr_validation.csv"

TARGET_COLUMNS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]

PATTERN = re.compile(
    r"(\d+)\s*Years?:?\s*(-?[\d.]+)%",
    re.IGNORECASE,
)


def parse_analysis() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_FILE, header=1)

    parsed_rows = []
    failure_rows = []

    for _, row in df.iterrows():
        company_id = row["company_id"]

        for metric_type in TARGET_COLUMNS:
            raw_text = row[metric_type]

            if pd.isna(raw_text):
                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "source_text": "",
                        "reason": "Empty value",
                    }
                )
                continue

            text = str(raw_text).strip()
            match = PATTERN.search(text)

            if match:
                parsed_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "period_years": int(match.group(1)),
                        "value_pct": float(match.group(2)),
                    }
                )
            else:
                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "source_text": text,
                        "reason": "Pattern not matched",
                    }
                )

    parsed_df = pd.DataFrame(
        parsed_rows,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ],
    )

    failures_df = pd.DataFrame(
        failure_rows,
        columns=[
            "company_id",
            "metric_type",
            "source_text",
            "reason",
        ],
    )

    parsed_df.to_csv(PARSED_FILE, index=False)
    failures_df.to_csv(FAILURE_FILE, index=False)

    print("Day 29 parser completed")
    print("Parsed rows:", len(parsed_df))
    print("Failed rows:", len(failures_df))
    print("Created:", PARSED_FILE)
    print("Created:", FAILURE_FILE)


def validate_cagr() -> None:
    connection = sqlite3.connect(DATABASE_FILE)

    ratios_df = pd.read_sql_query(
        """
        SELECT
            company_id,
            revenue_cagr_5yr,
            pat_cagr_5yr
        FROM financial_ratios
        """,
        connection,
    )

    connection.close()

    # Ratio values are repeated for multiple years,
    # so keep only one row for each company.
    ratios_df = ratios_df.drop_duplicates(subset=["company_id"])

    parsed_df = pd.read_csv(PARSED_FILE)

    validation_rows = []

    for _, row in parsed_df.iterrows():
        if row["period_years"] != 5:
            continue

        company_id = row["company_id"]
        metric_type = row["metric_type"]

        company_ratio = ratios_df[
            ratios_df["company_id"] == company_id
        ]

        if company_ratio.empty:
            validation_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "parsed_value_pct": row["value_pct"],
                    "computed_value_pct": "",
                    "divergence_pct": "",
                    "manual_review_flag": True,
                    "reason": "Company not found in financial_ratios",
                }
            )
            continue

        if metric_type == "compounded_sales_growth":
            computed_value = company_ratio.iloc[0][
                "revenue_cagr_5yr"
            ]

        elif metric_type == "compounded_profit_growth":
            computed_value = company_ratio.iloc[0][
                "pat_cagr_5yr"
            ]

        else:
            continue

        parsed_value = float(row["value_pct"])

        if pd.isna(computed_value):
            validation_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "parsed_value_pct": parsed_value,
                    "computed_value_pct": "",
                    "divergence_pct": "",
                    "manual_review_flag": True,
                    "reason": "Computed CAGR value is missing",
                }
            )
            continue

        computed_value = float(computed_value)
        divergence = abs(parsed_value - computed_value)

        validation_rows.append(
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "parsed_value_pct": parsed_value,
                "computed_value_pct": round(computed_value, 2),
                "divergence_pct": round(divergence, 2),
                "manual_review_flag": divergence > 5,
                "reason": (
                    "Divergence above 5%"
                    if divergence > 5
                    else "Within acceptable range"
                ),
            }
        )

    validation_df = pd.DataFrame(
        validation_rows,
        columns=[
            "company_id",
            "metric_type",
            "parsed_value_pct",
            "computed_value_pct",
            "divergence_pct",
            "manual_review_flag",
            "reason",
        ],
    )

    validation_df.to_csv(VALIDATION_FILE, index=False)

    manual_review_count = (
        validation_df["manual_review_flag"].sum()
        if not validation_df.empty
        else 0
    )

    print("\nCAGR validation completed")
    print("Validation rows:", len(validation_df))
    print("Manual review rows:", manual_review_count)
    print("Created:", VALIDATION_FILE)


if __name__ == "__main__":
    parse_analysis()
    validate_cagr()