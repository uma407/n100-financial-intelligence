import sqlite3
import pandas as pd

from ratios import (
    net_profit_margin,
    operating_profit_margin,
    asset_turnover,
)

from cashflow_kpis import (
    free_cash_flow,
    capex_intensity,
    fcf_conversion_rate,
)

from cagr import revenue_cagr, pat_cagr, eps_cagr


DB_PATH = "nifty100.db"
OUTPUT_LOG = "output/day12_data_limitations.log"


def safe_get(row, col, default=0):
    if col in row.index and pd.notna(row[col]):
        return row[col]
    return default


def add_column_if_missing(conn, table_name, column_name, column_type):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [row[1] for row in cur.fetchall()]

    if column_name not in existing_columns:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def ensure_kpi_columns(conn):
    columns = {
        "net_profit_margin_pct": "REAL",
        "operating_profit_margin_pct": "REAL",
        "asset_turnover": "REAL",
        "free_cash_flow_cr": "REAL",
        "capex_cr": "REAL",
        "fcf_conversion_rate_pct": "REAL",
        "earnings_per_share": "REAL",
        "cash_from_operations_cr": "REAL",
        "revenue_cagr_5yr": "REAL",
        "pat_cagr_5yr": "REAL",
        "eps_cagr_5yr": "REAL",
        "composite_quality_score": "REAL",
    }

    for col, typ in columns.items():
        add_column_if_missing(conn, "financial_ratios", col, typ)


def write_data_limitations_log():
    limitations = [
        "Day 12 Data Limitation Log",
        "Some Sprint 2 KPIs could not be computed because the current SQLite schema does not contain required source columns.",
        "",
        "Unavailable source columns:",
        "- equity_capital",
        "- reserves",
        "- borrowings",
        "- interest",
        "- other_income",
        "- dividend",
        "- investments",
        "",
        "KPIs not computed from current DB schema:",
        "- return_on_equity_pct",
        "- debt_to_equity",
        "- interest_coverage",
        "- book_value_per_share",
        "- dividend_payout_ratio_pct",
        "- total_debt_cr",
        "",
        "Available KPIs populated:",
        "- net_profit_margin_pct",
        "- operating_profit_margin_pct",
        "- asset_turnover",
        "- free_cash_flow_cr",
        "- capex_cr",
        "- fcf_conversion_rate_pct",
        "- earnings_per_share",
        "- cash_from_operations_cr",
        "- revenue_cagr_5yr",
        "- pat_cagr_5yr",
        "- eps_cagr_5yr",
        "- composite_quality_score",
    ]

    with open(OUTPUT_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(limitations))


def main():
    conn = sqlite3.connect(DB_PATH)

    ensure_kpi_columns(conn)
    write_data_limitations_log()

    pnl = pd.read_sql_query("SELECT * FROM profitandloss", conn)
    bs = pd.read_sql_query("SELECT * FROM balancesheet", conn)
    cf = pd.read_sql_query("SELECT * FROM cashflow", conn)
    fr = pd.read_sql_query("SELECT * FROM financial_ratios", conn)

    updated = 0

    for _, row in fr.iterrows():
        company_id = row["company_id"]
        year = row["year"]

        pnl_row = pnl[(pnl["company_id"] == company_id) & (pnl["year"] == year)]
        bs_row = bs[(bs["company_id"] == company_id) & (bs["year"] == year)]
        cf_row = cf[(cf["company_id"] == company_id) & (cf["year"] == year)]

        if pnl_row.empty:
            continue

        pnl_row = pnl_row.iloc[0]
        bs_row = bs_row.iloc[0] if not bs_row.empty else pd.Series()
        cf_row = cf_row.iloc[0] if not cf_row.empty else pd.Series()

        sales = safe_get(pnl_row, "sales")
        net_profit = safe_get(pnl_row, "net_profit")
        operating_profit = safe_get(pnl_row, "operating_profit")
        eps = safe_get(pnl_row, "eps")

        total_assets = safe_get(bs_row, "total_assets")

        operating_activity = safe_get(cf_row, "operating_activity")
        investing_activity = safe_get(cf_row, "investing_activity")

        npm = net_profit_margin(net_profit, sales)
        opm = operating_profit_margin(operating_profit, sales)
        at = asset_turnover(sales, total_assets)

        fcf = free_cash_flow(operating_activity, investing_activity)
        capex_value, _ = capex_intensity(investing_activity, sales)
        fcf_conversion = fcf_conversion_rate(fcf, operating_profit)

        company_pnl = pnl[pnl["company_id"] == company_id].sort_values("year")

        revenue_values = company_pnl["sales"].tolist()
        pat_values = company_pnl["net_profit"].tolist()
        eps_values = company_pnl["eps"].tolist()

        rev_cagr, _ = revenue_cagr(revenue_values, 5)
        pat_cagr_value, _ = pat_cagr(pat_values, 5)
        eps_cagr_value, _ = eps_cagr(eps_values, 5)

        available_scores = [
            npm,
            opm,
            at,
            fcf_conversion,
            rev_cagr,
            pat_cagr_value,
            eps_cagr_value,
        ]

        valid_scores = [x for x in available_scores if x is not None]
        composite_score = sum(valid_scores) / len(valid_scores) if valid_scores else None

        conn.execute(
            """
            UPDATE financial_ratios
            SET
                net_profit_margin_pct = ?,
                operating_profit_margin_pct = ?,
                asset_turnover = ?,
                free_cash_flow_cr = ?,
                capex_cr = ?,
                fcf_conversion_rate_pct = ?,
                earnings_per_share = ?,
                cash_from_operations_cr = ?,
                revenue_cagr_5yr = ?,
                pat_cagr_5yr = ?,
                eps_cagr_5yr = ?,
                composite_quality_score = ?
            WHERE company_id = ? AND year = ?
            """,
            (
                npm,
                opm,
                at,
                fcf,
                capex_value,
                fcf_conversion,
                eps,
                operating_activity,
                rev_cagr,
                pat_cagr_value,
                eps_cagr_value,
                composite_score,
                company_id,
                year,
            ),
        )

        updated += 1

    conn.commit()

    row_count = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]

    non_null_counts = conn.execute("""
        SELECT
            COUNT(net_profit_margin_pct),
            COUNT(operating_profit_margin_pct),
            COUNT(asset_turnover),
            COUNT(free_cash_flow_cr),
            COUNT(capex_cr),
            COUNT(fcf_conversion_rate_pct),
            COUNT(earnings_per_share),
            COUNT(cash_from_operations_cr),
            COUNT(revenue_cagr_5yr),
            COUNT(pat_cagr_5yr),
            COUNT(eps_cagr_5yr),
            COUNT(composite_quality_score)
        FROM financial_ratios
    """).fetchone()

    print("financial_ratios row count:", row_count)
    print("Rows updated:", updated)
    print("Non-null KPI counts:")
    print(non_null_counts)
    print("Data limitation log saved:", OUTPUT_LOG)

    conn.close()


if __name__ == "__main__":
    main()