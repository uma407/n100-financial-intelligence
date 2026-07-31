import re
import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_FILE = PROJECT_ROOT / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "pros_cons_generated.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MIN_CONFIDENCE = 60


def extract_year(value):
    """Convert values such as 'Mar 2024' into 2024."""
    match = re.search(r"\d{4}", str(value))

    if match:
        return int(match.group())

    return 0


def load_data():
    connection = sqlite3.connect(DB_FILE)

    companies = pd.read_sql_query(
        "SELECT * FROM companies",
        connection,
    )

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        connection,
    )

    profit_loss = pd.read_sql_query(
        "SELECT * FROM profitandloss",
        connection,
    )

    balance_sheet = pd.read_sql_query(
        "SELECT * FROM balancesheet",
        connection,
    )

    sectors = pd.read_sql_query(
        "SELECT * FROM sectors",
        connection,
    )

    connection.close()

    for dataframe in [
        ratios,
        profit_loss,
        balance_sheet,
    ]:
        dataframe["year_number"] = dataframe["year"].apply(
            extract_year
        )

        dataframe.sort_values(
            ["company_id", "year_number"],
            inplace=True,
        )

    return {
        "companies": companies,
        "ratios": ratios,
        "profit_loss": profit_loss,
        "balance_sheet": balance_sheet,
        "sectors": sectors,
    }


def add_signal(
    rows,
    company_id,
    signal_type,
    rule_id,
    text,
    confidence,
):
    """Add a signal only when confidence is above 60%."""
    if confidence <= MIN_CONFIDENCE:
        return

    rows.append(
        {
            "company_id": company_id,
            "type": signal_type,
            "rule_id": rule_id,
            "text": text,
            "confidence_pct": confidence,
        }
    )


def get_latest(dataframe):
    if dataframe.empty:
        return None

    return dataframe.sort_values(
        "year_number"
    ).iloc[-1]


def get_numeric_values(dataframe, column, count):
    if column not in dataframe.columns:
        return []

    values = (
        pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )
        .dropna()
        .tail(count)
        .tolist()
    )

    return values


def strictly_increasing(values):
    return (
        len(values) >= 2
        and all(
            current > previous
            for previous, current in zip(
                values,
                values[1:],
            )
        )
    )


def strictly_decreasing(values):
    return (
        len(values) >= 2
        and all(
            current < previous
            for previous, current in zip(
                values,
                values[1:],
            )
        )
    )


def is_financial_sector(sector):
    sector_text = str(sector).lower()

    financial_keywords = [
        "financial",
        "bank",
        "insurance",
        "finance",
        "nbfc",
    ]

    return any(
        keyword in sector_text
        for keyword in financial_keywords
    )


def generate_company_signals(
    company_id,
    ratios_history,
    pl_history,
    bs_history,
    sector,
):
    signals = []

    latest_ratio = get_latest(ratios_history)
    latest_pl = get_latest(pl_history)
    latest_bs = get_latest(bs_history)

    if latest_ratio is None:
        return signals

    # =====================================================
    # PRO RULE 1
    # ROE above 20% for at least three consecutive years
    # =====================================================
    roe_3yr = get_numeric_values(
        ratios_history,
        "roe",
        3,
    )

    if (
        len(roe_3yr) == 3
        and all(value > 20 for value in roe_3yr)
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_01",
            (
                "Consistently high return on equity above "
                "20% demonstrates exceptional capital efficiency"
            ),
            95,
        )

    # =====================================================
    # PRO RULE 2
    # FCF positive for five consecutive years
    # =====================================================
    fcf_5yr = get_numeric_values(
        ratios_history,
        "free_cash_flow_cr",
        5,
    )

    if (
        len(fcf_5yr) == 5
        and all(value > 0 for value in fcf_5yr)
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_02",
            (
                "Strong free cash flow generation over 5 years "
                "signals healthy business fundamentals"
            ),
            94,
        )

    # =====================================================
    # PRO RULE 3
    # Debt-to-equity equal to zero
    # =====================================================
    debt_to_equity = latest_ratio.get(
        "debt_to_equity"
    )

    if (
        pd.notna(debt_to_equity)
        and float(debt_to_equity) == 0
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_03",
            (
                "Debt-free balance sheet provides financial "
                "flexibility and eliminates interest burden"
            ),
            98,
        )

    # =====================================================
    # PRO RULE 4
    # Revenue CAGR above 15%
    # =====================================================
    revenue_cagr = latest_ratio.get(
        "revenue_cagr_5yr"
    )

    if (
        pd.notna(revenue_cagr)
        and float(revenue_cagr) > 15
    ):
        confidence = min(
            99,
            int(75 + float(revenue_cagr)),
        )

        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_04",
            (
                "Revenue growing at above 15% CAGR over 5 years "
                "reflects strong business momentum"
            ),
            confidence,
        )

    # =====================================================
    # PRO RULE 5
    # Operating profit margin above 25%
    # =====================================================
    operating_margin = latest_ratio.get(
        "operating_profit_margin_pct"
    )

    if (
        pd.notna(operating_margin)
        and float(operating_margin) > 25
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_05",
            (
                "Operating profit margin above 25% indicates "
                "strong pricing power and cost discipline"
            ),
            92,
        )

    # =====================================================
    # PRO RULE 6
    # PAT CAGR above 20%
    # =====================================================
    pat_cagr = latest_ratio.get(
        "pat_cagr_5yr"
    )

    if (
        pd.notna(pat_cagr)
        and float(pat_cagr) > 20
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_06",
            (
                "Net profit compounding at above 20% over "
                "5 years creates significant shareholder value"
            ),
            95,
        )

    # =====================================================
    # PRO RULE 7
    # Interest coverage above 10 or debt free
    # =====================================================
    interest_coverage = latest_ratio.get(
        "interest_coverage"
    )

    debt_free = (
        pd.notna(debt_to_equity)
        and float(debt_to_equity) == 0
    )

    if (
        debt_free
        or (
            pd.notna(interest_coverage)
            and float(interest_coverage) > 10
        )
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_07",
            (
                "Very high interest coverage ratio reflects "
                "negligible financial stress from debt servicing"
            ),
            94,
        )

    # =====================================================
    # PRO RULE 8
    # Dividend yield is unavailable in the database.
    # Use positive dividend payout backed by positive FCF.
    # =====================================================
    dividend_payout = latest_ratio.get(
        "dividend_payout_ratio_pct"
    )

    latest_fcf = latest_ratio.get(
        "free_cash_flow_cr"
    )

    if (
        pd.notna(dividend_payout)
        and float(dividend_payout) > 0
        and pd.notna(latest_fcf)
        and float(latest_fcf) > 0
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_08",
            (
                "Dividend distribution backed by positive free "
                "cash flow indicates sustainable shareholder returns"
            ),
            82,
        )

    # =====================================================
    # PRO RULE 9
    # EPS CAGR above 15%
    # =====================================================
    eps_cagr = latest_ratio.get(
        "eps_cagr_5yr"
    )

    if (
        pd.notna(eps_cagr)
        and float(eps_cagr) > 15
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_09",
            (
                "Earnings per share growing above 15% CAGR "
                "indicates strong earnings quality and compounding"
            ),
            93,
        )

    # =====================================================
    # PRO RULE 10
    # ROE improving for three consecutive years
    # =====================================================
    if (
        len(roe_3yr) == 3
        and strictly_increasing(roe_3yr)
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_10",
            (
                "Return on equity improving for 3 consecutive "
                "years shows strengthening business quality"
            ),
            88,
        )

    # =====================================================
    # PRO RULE 11
    # PAT CAGR greater than Revenue CAGR
    # =====================================================
    if (
        pd.notna(revenue_cagr)
        and pd.notna(pat_cagr)
        and float(pat_cagr) > float(revenue_cagr)
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_11",
            (
                "Revenue growing slower than profits shows improving "
                "operating leverage and scale benefits"
            ),
            87,
        )

    # =====================================================
    # PRO RULE 12
    # Assets rising while debt declines
    # =====================================================
    assets_3yr = get_numeric_values(
        bs_history,
        "total_assets",
        3,
    )

    debt_3yr = get_numeric_values(
        ratios_history,
        "total_debt_cr",
        3,
    )

    if (
        len(assets_3yr) == 3
        and len(debt_3yr) == 3
        and strictly_increasing(assets_3yr)
        and strictly_decreasing(debt_3yr)
    ):
        add_signal(
            signals,
            company_id,
            "pro",
            "PRO_12",
            (
                "Growing asset base funded by internal accruals "
                "reflects self-sustaining growth"
            ),
            90,
        )

    # =====================================================
    # CON RULE 1
    # D/E above 2 for non-financial companies
    # =====================================================
    if (
        pd.notna(debt_to_equity)
        and float(debt_to_equity) > 2
        and not is_financial_sector(sector)
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_01",
            (
                f"Debt-to-equity ratio of "
                f"{float(debt_to_equity):.2f} is elevated for a "
                "non-financial company and warrants monitoring"
            ),
            94,
        )

    # =====================================================
    # CON RULE 2
    # FCF negative for three consecutive years
    # =====================================================
    fcf_3yr = get_numeric_values(
        ratios_history,
        "free_cash_flow_cr",
        3,
    )

    if (
        len(fcf_3yr) == 3
        and all(value < 0 for value in fcf_3yr)
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_02",
            (
                "Free cash flow negative for 3 consecutive years "
                "raises concern about cash generation quality"
            ),
            95,
        )

    # =====================================================
    # CON RULE 3
    # Operating margin declining for three years
    # =====================================================
    opm_3yr = get_numeric_values(
        ratios_history,
        "operating_profit_margin_pct",
        3,
    )

    if (
        len(opm_3yr) == 3
        and strictly_decreasing(opm_3yr)
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_03",
            (
                "Operating margins declining for 3 consecutive "
                "years suggest pricing or cost pressure"
            ),
            89,
        )

    # =====================================================
    # CON RULE 4
    # Latest net profit negative
    # =====================================================
    if latest_pl is not None:
        latest_net_profit = latest_pl.get(
            "net_profit"
        )

        if (
            pd.notna(latest_net_profit)
            and float(latest_net_profit) < 0
        ):
            add_signal(
                signals,
                company_id,
                "con",
                "CON_04",
                (
                    "Company reported a net loss in the most "
                    "recent financial year"
                ),
                98,
            )

    # =====================================================
    # CON RULE 5
    # Revenue declining for two consecutive years
    # =====================================================
    sales_3yr = get_numeric_values(
        pl_history,
        "sales",
        3,
    )

    if (
        len(sales_3yr) == 3
        and strictly_decreasing(sales_3yr)
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_05",
            (
                "Revenue contraction over 2 consecutive years "
                "indicates demand weakness or market share loss"
            ),
            92,
        )

    # =====================================================
    # CON RULE 6
    # Interest coverage below 1.5
    # =====================================================
    if (
        pd.notna(interest_coverage)
        and float(interest_coverage) < 1.5
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_06",
            (
                "Interest coverage ratio below 1.5x indicates the "
                "company is at risk of not meeting its debt obligations"
            ),
            97,
        )

    # =====================================================
    # CON RULE 7
    # Dividend payout above 100%
    # =====================================================
    if (
        pd.notna(dividend_payout)
        and float(dividend_payout) > 100
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_07",
            (
                "Dividend payout ratio above 100% means the company "
                "is paying dividends from reserves, which is unsustainable"
            ),
            94,
        )

    # =====================================================
    # CON RULE 8
    # Debt-to-equity rising for three years
    # =====================================================
    debt_equity_3yr = get_numeric_values(
        ratios_history,
        "debt_to_equity",
        3,
    )

    if (
        len(debt_equity_3yr) == 3
        and strictly_increasing(debt_equity_3yr)
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_08",
            (
                "Rising debt-to-equity ratio over 3 years suggests "
                "increasing financial leverage risk"
            ),
            90,
        )

    # =====================================================
    # CON RULE 9
    # EPS declining for three consecutive years
    # =====================================================
    eps_3yr = get_numeric_values(
        pl_history,
        "eps",
        3,
    )

    if (
        len(eps_3yr) == 3
        and strictly_decreasing(eps_3yr)
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_09",
            (
                "Earnings per share declining for 3 consecutive "
                "years reflects deteriorating profitability"
            ),
            91,
        )

    # =====================================================
    # CON RULE 10
    # ROCE unavailable; ROE below 10% is used as a proxy.
    # =====================================================
    latest_roe = latest_ratio.get("roe")

    if (
        pd.notna(latest_roe)
        and float(latest_roe) < 10
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_10",
            (
                "Return on capital proxy below 10% suggests the "
                "business is not generating sufficient returns"
            ),
            75,
        )

    # =====================================================
    # CON RULE 11
    # Debt above three times operating profit.
    # Operating profit is used as an EBITDA proxy.
    # =====================================================
    total_debt = latest_ratio.get(
        "total_debt_cr"
    )

    if latest_pl is not None:
        operating_profit = latest_pl.get(
            "operating_profit"
        )

        if (
            pd.notna(total_debt)
            and pd.notna(operating_profit)
            and float(operating_profit) > 0
            and float(total_debt)
            / float(operating_profit)
            > 3
        ):
            add_signal(
                signals,
                company_id,
                "con",
                "CON_11",
                (
                    "Debt exceeding 3 times operating earnings is "
                    "a high leverage ratio and limits financial flexibility"
                ),
                88,
            )

    # =====================================================
    # CON RULE 12
    # Revenue CAGR below 5%
    # =====================================================
    if (
        pd.notna(revenue_cagr)
        and float(revenue_cagr) < 5
    ):
        add_signal(
            signals,
            company_id,
            "con",
            "CON_12",
            (
                "Revenue growing at below 5% over 5 years lags "
                "inflation and suggests limited business momentum"
            ),
            90,
        )

    return signals


def add_missing_company_signals(
    dataframe,
    company_ids,
):
    """Ensure every company has at least one pro and one con."""
    extra_rows = []

    for company_id in company_ids:
        company_rows = dataframe[
            dataframe["company_id"] == company_id
        ]

        has_pro = (
            company_rows["type"].eq("pro").any()
            if not company_rows.empty
            else False
        )

        has_con = (
            company_rows["type"].eq("con").any()
            if not company_rows.empty
            else False
        )

        if not has_pro:
            extra_rows.append(
                {
                    "company_id": company_id,
                    "type": "pro",
                    "rule_id": "PRO_FALLBACK",
                    "text": (
                        "Available financial information provides a "
                        "base for continued quantitative evaluation"
                    ),
                    "confidence_pct": 61,
                }
            )

        if not has_con:
            extra_rows.append(
                {
                    "company_id": company_id,
                    "type": "con",
                    "rule_id": "CON_FALLBACK",
                    "text": (
                        "No major risk rule was triggered, but future "
                        "execution and financial performance require monitoring"
                    ),
                    "confidence_pct": 61,
                }
            )

    if extra_rows:
        dataframe = pd.concat(
            [
                dataframe,
                pd.DataFrame(extra_rows),
            ],
            ignore_index=True,
        )

    return dataframe


def generate_pros_cons():
    data = load_data()

    ratios = data["ratios"]
    profit_loss = data["profit_loss"]
    balance_sheet = data["balance_sheet"]
    sectors = data["sectors"]

    companies = data["companies"]

    company_ids = sorted(
       companies["id"]
       .dropna()
       .astype(str)
       .unique()
)
    

    output_rows = []

    for company_id in company_ids:
        company_ratios = ratios[
            ratios["company_id"] == company_id
        ].copy()

        company_pl = profit_loss[
            profit_loss["company_id"] == company_id
        ].copy()

        company_bs = balance_sheet[
            balance_sheet["company_id"] == company_id
        ].copy()

        sector_match = sectors[
            sectors["company_id"] == company_id
        ]

        sector = (
            sector_match.iloc[0]["broad_sector"]
            if not sector_match.empty
            else "Unknown"
        )

        signals = generate_company_signals(
            company_id=company_id,
            ratios_history=company_ratios,
            pl_history=company_pl,
            bs_history=company_bs,
            sector=sector,
        )

        output_rows.extend(signals)

    output_df = pd.DataFrame(
        output_rows,
        columns=[
            "company_id",
            "type",
            "rule_id",
            "text",
            "confidence_pct",
        ],
    )

    output_df = output_df[
        output_df["confidence_pct"] > MIN_CONFIDENCE
    ]

    output_df = output_df.drop_duplicates(
        subset=[
            "company_id",
            "type",
            "rule_id",
        ]
    )

    output_df = add_missing_company_signals(
        output_df,
        company_ids,
    )

    output_df = output_df.sort_values(
        [
            "company_id",
            "type",
            "confidence_pct",
        ],
        ascending=[
            True,
            True,
            False,
        ],
    ).reset_index(drop=True)

    output_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    pro_companies = output_df[
        output_df["type"] == "pro"
    ]["company_id"].nunique()

    con_companies = output_df[
        output_df["type"] == "con"
    ]["company_id"].nunique()

    missing_pro = set(company_ids) - set(
        output_df[
            output_df["type"] == "pro"
        ]["company_id"]
    )

    missing_con = set(company_ids) - set(
        output_df[
            output_df["type"] == "con"
        ]["company_id"]
    )

    print("Day 30 Pros/Cons Generator completed")
    print("Companies processed:", len(company_ids))
    print("Total output rows:", len(output_df))
    print(
        "Pro rows:",
        len(output_df[output_df["type"] == "pro"]),
    )
    print(
        "Con rows:",
        len(output_df[output_df["type"] == "con"]),
    )
    print("Companies with at least one pro:", pro_companies)
    print("Companies with at least one con:", con_companies)
    print("Missing pro companies:", len(missing_pro))
    print("Missing con companies:", len(missing_con))
    print("Created:", OUTPUT_FILE)


if __name__ == "__main__":
    generate_pros_cons()