import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_FILE = PROJECT_ROOT / "nifty100.db"
TEARSHEET_DIR = PROJECT_ROOT / "reports" / "tearsheets"
OUTPUT_DIR = PROJECT_ROOT / "output"

INDEX_FILE = OUTPUT_DIR / "tearsheet_index.csv"
MISSING_FILE = OUTPUT_DIR / "missing_tearsheets.csv"


def generate_tearsheet_index():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)

    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        ORDER BY id
        """,
        conn,
    )

    conn.close()

    index_rows = []
    missing_rows = []

    for _, company in companies.iterrows():
        company_id = company["company_id"]
        company_name = company["company_name"]

        pdf_name = f"{company_id}_tearsheet.pdf"
        pdf_path = TEARSHEET_DIR / pdf_name

        exists = pdf_path.exists()

        index_rows.append(
            {
                "company_id": company_id,
                "company_name": company_name,
                "pdf_file": pdf_name,
                "pdf_path": str(pdf_path),
                "status": "Available" if exists else "Missing",
            }
        )

        if not exists:
            missing_rows.append(
                {
                    "company_id": company_id,
                    "company_name": company_name,
                    "expected_pdf": pdf_name,
                }
            )

    index_df = pd.DataFrame(index_rows)

    missing_df = pd.DataFrame(
        missing_rows,
        columns=[
            "company_id",
            "company_name",
            "expected_pdf",
        ],
    )

    index_df.to_csv(
        INDEX_FILE,
        index=False,
    )

    missing_df.to_csv(
        MISSING_FILE,
        index=False,
    )

    print("Day 35 tearsheet index completed.")
    print("Total companies:", len(index_df))
    print(
        "Available PDFs:",
        (index_df["status"] == "Available").sum(),
    )
    print(
        "Missing PDFs:",
        (index_df["status"] == "Missing").sum(),
    )
    print("Index file:", INDEX_FILE)
    print("Missing report:", MISSING_FILE)


if __name__ == "__main__":
    generate_tearsheet_index()