from pathlib import Path
import sqlite3
import pandas as pd

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from normaliser import normalize_year, normalize_ticker

RAW_DATA_PATH = Path("data/raw")
OUTPUT_PATH = Path("output")
DB_PATH = Path("nifty100.db")
SCHEMA_PATH = Path("db/schema.sql")

FILES = {
    "companies": ("companies.xlsx", 1),
    "profitandloss": ("profitandloss.xlsx", 1),
    "balancesheet": ("balancesheet.xlsx", 1),
    "cashflow": ("cashflow.xlsx", 1),
    "analysis": ("analysis.xlsx", 1),
    "documents": ("documents.xlsx", 1),
    "prosandcons": ("prosandcons.xlsx", 1),
    "sectors": ("sectors.xlsx", 0),
    "stock_prices": ("stock_prices.xlsx", 0),
    "financial_ratios": ("financial_ratios.xlsx", 0),
    "peer_groups": ("peer_groups.xlsx", 0),
}


def clean_column_names(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def load_excel_file(file_name, header):
    path = RAW_DATA_PATH / file_name
    df = pd.read_excel(path, header=header)
    df = clean_column_names(df)

    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)

    if file_name == "companies.xlsx" and "id" in df.columns:
        df["id"] = df["id"].apply(normalize_ticker)

    if "year" in df.columns:
        df["year"] = df["year"].apply(normalize_year)

    if "annual_report" in df.columns:
        df = df.rename(columns={"annual_report": "document_url"})

    if "return_on_equity_pct" in df.columns:
        df = df.rename(columns={"return_on_equity_pct": "roe"})

    if "net_profit_margin_pct" in df.columns:
        df = df.rename(columns={"net_profit_margin_pct": "net_profit_margin"})

    return df


def create_database():
    conn = sqlite3.connect(DB_PATH)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        schema = file.read()

    conn.executescript(schema)
    conn.commit()
    return conn


def get_table_columns(conn, table_name):
    result = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in result]


def clear_tables(conn):
    tables = [
        "peer_groups",
        "financial_ratios",
        "stock_prices",
        "sectors",
        "prosandcons",
        "documents",
        "analysis",
        "cashflow",
        "balancesheet",
        "profitandloss",
        "companies",
    ]

    for table in tables:
        conn.execute(f"DELETE FROM {table}")

    conn.commit()


def insert_dataframe(conn, table_name, df):
    table_cols = get_table_columns(conn, table_name)
    df = df[[col for col in df.columns if col in table_cols]]
    if table_name != "companies" and "company_id" in df.columns:
         valid_ids = pd.read_sql_query("SELECT id FROM companies", conn)["id"].tolist()
         df = df[df["company_id"].isin(valid_ids)]

    if df.empty:
        return 0

    cols = list(df.columns)
    placeholders = ",".join(["?"] * len(cols))
    col_names = ",".join(cols)

    sql = f"""
    INSERT OR REPLACE INTO {table_name} ({col_names})
    VALUES ({placeholders})
    """

    rows = df.where(pd.notna(df), None).values.tolist()
    conn.executemany(sql, rows)
    conn.commit()

    return len(rows)


def run_load():
    OUTPUT_PATH.mkdir(exist_ok=True)

    conn = create_database()
    conn.execute("PRAGMA foreign_keys = OFF")

    clear_tables(conn)

    audit_rows = []

    load_order = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "sectors",
        "stock_prices",
        "financial_ratios",
        "peer_groups",
    ]

    for table_name in load_order:
        file_name, header = FILES[table_name]

        try:
            df = load_excel_file(file_name, header)
            rows_read = len(df)
            rows_loaded = insert_dataframe(conn, table_name, df)
            rejected = rows_read - rows_loaded
            status = "SUCCESS"

        except Exception as e:
            rows_read = 0
            rows_loaded = 0
            rejected = 0
            status = f"FAILED: {e}"

        audit_rows.append({
            "table": table_name,
            "source_file": file_name,
            "rows_read": rows_read,
            "rows_loaded": rows_loaded,
            "rejected": rejected,
            "status": status
        })

    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(OUTPUT_PATH / "load_audit.csv", index=False)

    print("\nLOAD AUDIT")
    print(audit_df)

    print("\nROW COUNTS")
    for table in load_order:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:20} {count}")
    conn.execute("PRAGMA foreign_keys = ON")
    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    print(f"\nForeign Key Errors: {len(fk_errors)}")

    conn.close()


if __name__ == "__main__":
    run_load()