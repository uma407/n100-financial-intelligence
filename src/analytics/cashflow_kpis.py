import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_FILE = PROJECT_ROOT / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

INTELLIGENCE_FILE = OUTPUT_DIR / "cashflow_intelligence.xlsx"
DISTRESS_FILE = OUTPUT_DIR / "distress_alerts.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_year(value):
    """Convert year values such as 'Mar 2024' or '2024-03' to 2024."""
    match = re.search(r"\d{4}", str(value))

    if match:
        return int(match.group())

    return 0


def safe_divide(numerator, denominator):
    """Return numerator / denominator safely."""
    if pd.isna(numerator) or pd.isna(denominator):
        return np.nan

    if float(denominator) == 0:
        return np.nan

    return float(numerator) / float(denominator)


def calculate_cagr(values, years=5):
    """Calculate CAGR using the oldest and latest positive values."""
    clean_values = [
        float(value)
        for value in values
        if pd.notna(value)
    ]

    if len(clean_values) < 2:
        return np.nan

    selected = clean_values[-(years + 1):]

    start_value = selected[0]
    end_value = selected[-1]

    periods = len(selected) - 1

    if (
        start_value <= 0
        or end_value <= 0
        or periods <= 0
    ):
        return np.nan

    return (
        (end_value / start_value) ** (1 / periods) - 1
    ) * 100


def load_data():
    connection = sqlite3.connect(DATABASE_FILE)

    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        """,
        connection,
    )

    sectors = pd.read_sql_query(
        """
        SELECT
            company_id,
            broad_sector AS sector
        FROM sectors
        """,
        connection,
    )

    cashflow = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity,
            net_cash_flow
        FROM cashflow
        """,
        connection,
    )

    profit_loss = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            sales,
            net_profit
        FROM profitandloss
        """,
        connection,
    )

    ratios = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            free_cash_flow_cr,
            cash_from_operations_cr,
            total_debt_cr
        FROM financial_ratios
        """,
        connection,
    )

    connection.close()

    for dataframe in [
        cashflow,
        profit_loss,
        ratios,
    ]:
        dataframe["year_number"] = dataframe["year"].apply(
            extract_year
        )

        dataframe.sort_values(
            ["company_id", "year_number"],
            inplace=True,
        )

    return companies, sectors, cashflow, profit_loss, ratios


def classify_cfo_quality(score):
    if pd.isna(score):
        return "Data Unavailable"

    if score > 1:
        return "High Quality"

    if score >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def classify_capex_intensity(value):
    if pd.isna(value):
        return "Data Unavailable"

    if value < 3:
        return "Asset Light"

    if value <= 8:
        return "Moderate"

    return "Capital Intensive"


def classify_capital_allocation(cfo, cfi, cff):
    """Classify the latest-year cash flow pattern."""
    if any(pd.isna(value) for value in [cfo, cfi, cff]):
        return "Data Unavailable"

    if cfo < 0 and cff > 0:
        return "Distress Signal"

    if cfo > 0 and cfi < 0 and cff < 0:
        return "Reinvestor and Deleverager"

    if cfo > 0 and cfi < 0 and cff > 0:
        return "Aggressive Expansion"

    if cfo > 0 and cfi >= 0 and cff < 0:
        return "Cash Generator"

    if cfo > 0 and cfi >= 0 and cff >= 0:
        return "Cash Accumulator"

    if cfo < 0 and cfi < 0 and cff < 0:
        return "Cash Burn"

    if cfo < 0 and cfi >= 0 and cff > 0:
        return "Asset Sale Funded"

    if cfo < 0 and cfi >= 0 and cff <= 0:
        return "Contraction"

    return "Mixed Allocation"


def get_latest_row(dataframe):
    if dataframe.empty:
        return None

    return dataframe.sort_values(
        "year_number"
    ).iloc[-1]


def generate_cashflow_intelligence():
    (
        companies,
        sectors,
        cashflow,
        profit_loss,
        ratios,
    ) = load_data()

    output_rows = []
    distress_rows = []

    company_ids = sorted(
        companies["company_id"]
        .dropna()
        .astype(str)
        .unique()
    )

    for company_id in company_ids:
        company_cf = cashflow[
            cashflow["company_id"] == company_id
        ].copy()

        company_pl = profit_loss[
            profit_loss["company_id"] == company_id
        ].copy()

        company_ratios = ratios[
            ratios["company_id"] == company_id
        ].copy()

        sector_match = sectors[
            sectors["company_id"] == company_id
        ]

        sector = (
            sector_match.iloc[0]["sector"]
            if not sector_match.empty
            else "Unknown"
        )

        latest_cf = get_latest_row(company_cf)
        latest_pl = get_latest_row(company_pl)
        latest_ratio = get_latest_row(company_ratios)

        if latest_cf is None:
            output_rows.append(
                {
                    "company_id": company_id,
                    "sector": sector,
                    "cfo_quality_score": np.nan,
                    "cfo_quality_label": "Data Unavailable",
                    "capex_intensity_pct": np.nan,
                    "capex_label": "Data Unavailable",
                    "fcf_cagr_5yr": np.nan,
                    "fcf_conversion_pct": np.nan,
                    "distress_flag": False,
                    "deleveraging_flag": False,
                    "capital_allocation_label": "Data Unavailable",
                }
            )
            continue

        latest_year = int(latest_cf["year_number"])

        # -----------------------------------------
        # CFO Quality Score: average CFO / PAT
        # over the latest five matching years
        # -----------------------------------------
        cfo_pat_data = company_cf[
            [
                "year_number",
                "operating_activity",
            ]
        ].merge(
            company_pl[
                [
                    "year_number",
                    "net_profit",
                ]
            ],
            on="year_number",
            how="inner",
        )

        cfo_pat_data = cfo_pat_data.sort_values(
            "year_number"
        ).tail(5)

        quality_ratios = []

        for _, row in cfo_pat_data.iterrows():
            ratio = safe_divide(
                row["operating_activity"],
                row["net_profit"],
            )

            if pd.notna(ratio):
                quality_ratios.append(ratio)

        cfo_quality_score = (
            float(np.mean(quality_ratios))
            if quality_ratios
            else np.nan
        )

        cfo_quality_label = classify_cfo_quality(
            cfo_quality_score
        )

        # -----------------------------------------
        # CapEx Intensity
        # abs(investing activity) / sales × 100
        # -----------------------------------------
        latest_sales = np.nan

        if latest_pl is not None:
            latest_sales = latest_pl["sales"]

        capex_intensity_pct = safe_divide(
            abs(float(latest_cf["investing_activity"])),
            latest_sales,
        )

        if pd.notna(capex_intensity_pct):
            capex_intensity_pct *= 100

        capex_label = classify_capex_intensity(
            capex_intensity_pct
        )

        # -----------------------------------------
        # FCF CAGR for latest five-year period
        # -----------------------------------------
        fcf_values = (
            pd.to_numeric(
                company_ratios["free_cash_flow_cr"],
                errors="coerce",
            )
            .dropna()
            .tail(6)
            .tolist()
        )

        fcf_cagr_5yr = calculate_cagr(
            fcf_values,
            years=5,
        )

        # -----------------------------------------
        # FCF Conversion %
        # Latest FCF / latest CFO × 100
        # -----------------------------------------
        latest_fcf = np.nan

        if latest_ratio is not None:
            latest_fcf = latest_ratio[
                "free_cash_flow_cr"
            ]

        fcf_conversion_pct = safe_divide(
            latest_fcf,
            latest_cf["operating_activity"],
        )

        if pd.notna(fcf_conversion_pct):
            fcf_conversion_pct *= 100

        # -----------------------------------------
        # Distress Signal
        # CFO < 0 and CFF > 0
        # -----------------------------------------
        latest_cfo = float(
            latest_cf["operating_activity"]
        )

        latest_cfi = float(
            latest_cf["investing_activity"]
        )

        latest_cff = float(
            latest_cf["financing_activity"]
        )

        distress_flag = (
            latest_cfo < 0
            and latest_cff > 0
        )

        # -----------------------------------------
        # Deleveraging:
        # CFF < 0 and total debt declining YoY
        # -----------------------------------------
        debt_values = (
            company_ratios[
                [
                    "year_number",
                    "total_debt_cr",
                ]
            ]
            .dropna(subset=["total_debt_cr"])
            .sort_values("year_number")
            .tail(2)
        )

        debt_declining = False

        if len(debt_values) == 2:
            previous_debt = float(
                debt_values.iloc[0]["total_debt_cr"]
            )

            latest_debt = float(
                debt_values.iloc[1]["total_debt_cr"]
            )

            debt_declining = (
                latest_debt < previous_debt
            )

        deleveraging_flag = (
            latest_cff < 0
            and debt_declining
        )

        capital_allocation_label = (
            classify_capital_allocation(
                latest_cfo,
                latest_cfi,
                latest_cff,
            )
        )

        output_rows.append(
            {
                "company_id": company_id,
                "sector": sector,
                "cfo_quality_score": (
                    round(cfo_quality_score, 2)
                    if pd.notna(cfo_quality_score)
                    else np.nan
                ),
                "cfo_quality_label": cfo_quality_label,
                "capex_intensity_pct": (
                    round(capex_intensity_pct, 2)
                    if pd.notna(capex_intensity_pct)
                    else np.nan
                ),
                "capex_label": capex_label,
                "fcf_cagr_5yr": (
                    round(fcf_cagr_5yr, 2)
                    if pd.notna(fcf_cagr_5yr)
                    else np.nan
                ),
                "fcf_conversion_pct": (
                    round(fcf_conversion_pct, 2)
                    if pd.notna(fcf_conversion_pct)
                    else np.nan
                ),
                "distress_flag": distress_flag,
                "deleveraging_flag": deleveraging_flag,
                "capital_allocation_label": (
                    capital_allocation_label
                ),
            }
        )

        if distress_flag:
            latest_net_profit = (
                latest_pl["net_profit"]
                if latest_pl is not None
                else np.nan
            )

            distress_rows.append(
                {
                    "company_id": company_id,
                    "sector": sector,
                    "year": latest_year,
                    "cfo_value": latest_cfo,
                    "cff_value": latest_cff,
                    "latest_net_profit": latest_net_profit,
                    "distress_reason": (
                        "Operations generated negative cash flow "
                        "while financing activity raised cash"
                    ),
                }
            )

    intelligence_df = pd.DataFrame(
        output_rows,
        columns=[
            "company_id",
            "sector",
            "cfo_quality_score",
            "cfo_quality_label",
            "capex_intensity_pct",
            "capex_label",
            "fcf_cagr_5yr",
            "fcf_conversion_pct",
            "distress_flag",
            "deleveraging_flag",
            "capital_allocation_label",
        ],
    )

    distress_df = pd.DataFrame(
        distress_rows,
        columns=[
            "company_id",
            "sector",
            "year",
            "cfo_value",
            "cff_value",
            "latest_net_profit",
            "distress_reason",
        ],
    )

    intelligence_df.to_excel(
        INTELLIGENCE_FILE,
        index=False,
    )

    distress_df.to_csv(
        DISTRESS_FILE,
        index=False,
    )

    print("Day 31 Cash Flow Intelligence completed")
    print("Companies processed:", len(intelligence_df))
    print(
        "Distress companies:",
        int(intelligence_df["distress_flag"].sum()),
    )
    print(
        "Deleveraging companies:",
        int(intelligence_df["deleveraging_flag"].sum()),
    )

    print("\nCFO Quality Distribution:")
    print(
        intelligence_df[
            "cfo_quality_label"
        ].value_counts()
    )

    print("\nCapEx Distribution:")
    print(
        intelligence_df[
            "capex_label"
        ].value_counts()
    )

    print("\nCapital Allocation Distribution:")
    print(
        intelligence_df[
            "capital_allocation_label"
        ].value_counts()
    )

    print("\nCreated:", INTELLIGENCE_FILE)
    print("Created:", DISTRESS_FILE)


if __name__ == "__main__":
    generate_cashflow_intelligence()