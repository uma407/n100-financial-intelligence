import sqlite3
import os


DB_PATH = "nifty100.db"
OUTPUT_PATH = "output/ratio_edge_cases.log"


def write_log(lines):
    os.makedirs("output", exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    lines = []

    lines.append("Sprint 2 Day 13 - Ratio Edge Cases Log")
    lines.append("=" * 60)
    lines.append("")

    # Row count check
    row_count = cur.execute(
        "SELECT COUNT(*) FROM financial_ratios"
    ).fetchone()[0]

    lines.append(f"financial_ratios row count: {row_count}")
    lines.append("")

    if row_count < 1100:
        lines.append(
            "CATEGORY: data source issue | "
            "financial_ratios row count is below expected 1100 because current loaded dataset contains fewer valid rows."
        )

    # Null column check
    columns_to_check = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "asset_turnover",
        "free_cash_flow_cr",
        "capex_cr",
        "fcf_conversion_rate_pct",
        "earnings_per_share",
        "cash_from_operations_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    for col in columns_to_check:
        non_null_count = cur.execute(
            f"SELECT COUNT({col}) FROM financial_ratios"
        ).fetchone()[0]

        lines.append(
            f"COLUMN CHECK: {col} | non-null values: {non_null_count}"
        )

        if non_null_count == 0:
            lines.append(
                f"CATEGORY: data source issue | {col} has zero populated values."
            )

    lines.append("")

    # Known unavailable KPIs
    lines.append("Unavailable KPI Columns / Formula Limitations")
    lines.append("-" * 60)
    lines.append(
        "CATEGORY: data source issue | return_on_equity_pct cannot be recomputed accurately because equity_capital and reserves are not available in current DB schema."
    )
    lines.append(
        "CATEGORY: data source issue | debt_to_equity cannot be recomputed accurately because borrowings, equity_capital, and reserves are not available in current DB schema."
    )
    lines.append(
        "CATEGORY: data source issue | interest_coverage cannot be recomputed accurately because interest and other_income are not available in current DB schema."
    )
    lines.append(
        "CATEGORY: data source issue | book_value_per_share cannot be recomputed accurately because equity_capital and reserves are not available in current DB schema."
    )
    lines.append(
        "CATEGORY: data source issue | dividend_payout_ratio_pct cannot be recomputed accurately because dividend is not available in current DB schema."
    )
    lines.append(
        "CATEGORY: data source issue | total_debt_cr cannot be recomputed accurately because borrowings are not available in current DB schema."
    )

    lines.append("")

    # Financial sector carve-out note
    lines.append("Financial Sector / Bank Carve-Out")
    lines.append("-" * 60)
    lines.append(
        "CATEGORY: formula decision | Standard Debt-to-Equity warning is suppressed for Financials sector because high leverage is structurally normal for banks, NBFCs, and insurance companies."
    )
    lines.append(
        "CATEGORY: formula decision | Current DB schema does not contain broad_sector in financial_ratios; sector carve-out is documented here and should be applied during screener/dashboard integration."
    )

    lines.append("")

    # Sample anomaly checks using available columns
    negative_margin_count = cur.execute(
        """
        SELECT COUNT(*)
        FROM financial_ratios
        WHERE net_profit_margin_pct < 0
        """
    ).fetchone()[0]

    lines.append(
        f"CATEGORY: formula observation | Negative net profit margin records found: {negative_margin_count}"
    )

    high_capex_count = cur.execute(
        """
        SELECT COUNT(*)
        FROM financial_ratios
        WHERE capex_cr > 8
        """
    ).fetchone()[0]

    lines.append(
        f"CATEGORY: formula observation | Capital intensive records with capex_cr > 8: {high_capex_count}"
    )

    conn.close()

    write_log(lines)

    print(f"Edge case log saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()