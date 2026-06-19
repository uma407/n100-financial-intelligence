from pathlib import Path
import pandas as pd

from loader import load_all_files

OUTPUT_PATH = Path("output")
failures = []


def log_failure(rule, severity, table, message, count=0):
    failures.append({
        "rule": rule,
        "severity": severity,
        "table": table,
        "message": message,
        "count": count
    })


def dq01_pk_uniqueness(df, table, pk_col):
    if pk_col in df.columns:
        count = df[pk_col].duplicated().sum()
        if count > 0:
            log_failure("DQ-01", "CRITICAL", table, f"Duplicate primary key in {pk_col}", count)


def dq02_company_year_pk(df, table):
    if {"company_id", "year"}.issubset(df.columns):
        count = df.duplicated(subset=["company_id", "year"]).sum()
        if count > 0:
            log_failure("DQ-02", "CRITICAL", table, "Duplicate company_id and year records", count)


def dq03_fk_integrity(df, table, companies):
    if "company_id" in df.columns:
        valid_ids = set(companies["id"].dropna())
        invalid = ~df["company_id"].isin(valid_ids)
        count = invalid.sum()
        if count > 0:
            log_failure("DQ-03", "CRITICAL", table, "Invalid company_id FK found", count)


def dq04_bs_balance(bs):
    if {"total_assets", "total_liabilities"}.issubset(bs.columns):
        diff_pct = ((bs["total_assets"] - bs["total_liabilities"]).abs() / bs["total_assets"].replace(0, pd.NA)) * 100
        count = (diff_pct > 1).sum()
        if count > 0:
            log_failure("DQ-04", "WARNING", "balancesheet", "Balance sheet mismatch greater than 1%", count)


def dq05_opm_cross_check(pl):
    cols = {"sales", "operating_profit", "opm_percentage"}
    if cols.issubset(pl.columns):
        calculated = (pl["operating_profit"] / pl["sales"].replace(0, pd.NA)) * 100
        diff = (calculated - pl["opm_percentage"]).abs()
        count = (diff > 1).sum()
        if count > 0:
            log_failure("DQ-05", "WARNING", "profitandloss", "OPM percentage mismatch greater than 1%", count)


def dq06_positive_sales(pl):
    if "sales" in pl.columns:
        count = (pl["sales"] <= 0).sum()
        if count > 0:
            log_failure("DQ-06", "WARNING", "profitandloss", "Sales is zero or negative", count)


def dq07_net_cash_flow(cf):
    cols = {"operating_activity", "investing_activity", "financing_activity", "net_cash_flow"}
    if cols.issubset(cf.columns):
        calc = cf["operating_activity"] + cf["investing_activity"] + cf["financing_activity"]
        diff = (calc - cf["net_cash_flow"]).abs()
        count = (diff > 10).sum()
        if count > 0:
            log_failure("DQ-07", "WARNING", "cashflow", "Net cash flow mismatch greater than 10 crore", count)


def dq08_tax_rate(pl):
    if "tax_percentage" in pl.columns:
        count = ((pl["tax_percentage"] < 0) | (pl["tax_percentage"] > 60)).sum()
        if count > 0:
            log_failure("DQ-08", "WARNING", "profitandloss", "Tax percentage outside 0–60 range", count)


def dq09_dividend_cap(pl):
    if "dividend_payout" in pl.columns:
        count = (pl["dividend_payout"] > 300).sum()
        if count > 0:
            log_failure("DQ-09", "WARNING", "profitandloss", "Dividend payout unusually high", count)


def dq10_url_check(df, table):
    url_cols = [c for c in df.columns if "url" in c or "link" in c or "report" in c or "profile" in c or "website" in c]
    for col in url_cols:
        values = df[col].dropna().astype(str)
        count = (~values.str.startswith("http")).sum()
        if count > 0:
            log_failure("DQ-10", "WARNING", table, f"Invalid URL format in {col}", count)


def dq11_eps_sign(pl):
    if {"net_profit", "eps"}.issubset(pl.columns):
        count = ((pl["net_profit"] > 0) & (pl["eps"] <= 0)).sum()
        if count > 0:
            log_failure("DQ-11", "WARNING", "profitandloss", "EPS is non-positive while net profit is positive", count)


def dq12_bse_profile(companies):
    if "bse_profile" in companies.columns:
        count = companies["bse_profile"].isna().sum()
        if count > 0:
            log_failure("DQ-12", "WARNING", "companies", "Missing BSE profile link", count)


def dq13_year_coverage(df, table, min_years=5):
    if {"company_id", "year"}.issubset(df.columns):
        coverage = df.groupby("company_id")["year"].nunique()
        count = (coverage < min_years).sum()
        if count > 0:
            log_failure("DQ-13", "WARNING", table, f"Companies with less than {min_years} years coverage", count)


def dq14_null_required(df, table, required_cols):
    for col in required_cols:
        if col in df.columns:
            count = df[col].isna().sum()
            if count > 0:
                log_failure("DQ-14", "CRITICAL", table, f"Null values found in required column {col}", count)


def dq15_negative_assets(bs):
    asset_cols = [c for c in bs.columns if "asset" in c or "investment" in c]
    for col in asset_cols:
        count = (bs[col] < 0).sum()
        if count > 0:
            log_failure("DQ-15", "WARNING", "balancesheet", f"Negative value found in {col}", count)


def dq16_stock_price_check(prices):
    price_cols = ["open_price", "high_price", "low_price", "close_price", "adjusted_close"]
    for col in price_cols:
        if col in prices.columns:
            count = (prices[col] <= 0).sum()
            if count > 0:
                log_failure("DQ-16", "WARNING", "stock_prices", f"Non-positive stock price in {col}", count)


def save_failures():
    OUTPUT_PATH.mkdir(exist_ok=True)
    df = pd.DataFrame(failures)

    if df.empty:
        df = pd.DataFrame(columns=["rule", "severity", "table", "message", "count"])

    df.to_csv(OUTPUT_PATH / "validation_failures.csv", index=False)

    print("\nValidation report saved: output/validation_failures.csv")
    print(f"Total Issues Found: {len(df)}")

    critical_count = (df["severity"] == "CRITICAL").sum() if not df.empty else 0
    print(f"Critical Issues Found: {critical_count}")


def main():
    datasets = load_all_files()

    companies = datasets["companies"]
    pl = datasets["profitandloss"]
    bs = datasets["balancesheet"]
    cf = datasets["cashflow"]
    prices = datasets["stock_prices"]

    dq01_pk_uniqueness(companies, "companies", "id")

    for table, df in datasets.items():
        dq02_company_year_pk(df, table)
        dq03_fk_integrity(df, table, companies)
        dq10_url_check(df, table)

    dq04_bs_balance(bs)
    dq05_opm_cross_check(pl)
    dq06_positive_sales(pl)
    dq07_net_cash_flow(cf)
    dq08_tax_rate(pl)
    dq09_dividend_cap(pl)
    dq11_eps_sign(pl)
    dq12_bse_profile(companies)

    for table in ["profitandloss", "balancesheet", "cashflow"]:
        dq13_year_coverage(datasets[table], table)

    dq14_null_required(companies, "companies", ["id", "company_name"])
    dq14_null_required(pl, "profitandloss", ["company_id", "year", "sales"])
    dq14_null_required(bs, "balancesheet", ["company_id", "year", "total_assets", "total_liabilities"])
    dq14_null_required(cf, "cashflow", ["company_id", "year"])

    dq15_negative_assets(bs)
    dq16_stock_price_check(prices)

    save_failures()
    print("\nValidation Completed")


if __name__ == "__main__":
    main()