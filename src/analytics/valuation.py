from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MARKET_CAP_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "market_cap.xlsx"
)

DATABASE_FILE = PROJECT_ROOT / "nifty100.db"

OUTPUT_DIR = PROJECT_ROOT / "output"

SUMMARY_FILE = (
    OUTPUT_DIR
    / "valuation_summary.xlsx"
)

FLAGS_FILE = (
    OUTPUT_DIR
    / "valuation_flags.csv"
)


# ---------------------------------------------------------
# Required output columns
# ---------------------------------------------------------

OUTPUT_COLUMNS = [
    "company_id",
    "company_name",
    "sector",
    "P/E",
    "P/B",
    "EV/EBITDA",
    "FCF_yield_pct",
    "5yr_median_PE",
    "PE_vs_sector_median_pct",
    "flag",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def validate_files() -> None:
    """Check that required input files exist."""

    if not MARKET_CAP_FILE.exists():
        raise FileNotFoundError(
            f"Market-cap file not found: {MARKET_CAP_FILE}"
        )

    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {DATABASE_FILE}"
        )


def load_market_cap_data() -> pd.DataFrame:
    """Load and validate market-cap valuation data."""

    dataframe = pd.read_excel(MARKET_CAP_FILE)

    required_columns = [
        "company_id",
        "year",
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns in market_cap.xlsx: "
            + ", ".join(missing_columns)
        )

    dataframe = dataframe.copy()

    dataframe["company_id"] = (
        dataframe["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    numeric_columns = [
        "year",
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = dataframe.dropna(
        subset=[
            "company_id",
            "year",
        ]
    )

    dataframe["year"] = dataframe["year"].astype(int)

    return dataframe


def load_company_data(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Load company names from SQLite."""

    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        """,
        connection,
    )

    companies["company_id"] = (
        companies["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return companies.drop_duplicates(
        subset=["company_id"]
    )


def load_sector_data(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Load broad-sector information."""

    sectors = pd.read_sql_query(
        """
        SELECT
            company_id,
            broad_sector
        FROM sectors
        """,
        connection,
    )

    sectors["company_id"] = (
        sectors["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    sectors["broad_sector"] = (
        sectors["broad_sector"]
        .fillna("Unclassified")
        .astype(str)
        .str.strip()
    )

    return sectors.drop_duplicates(
        subset=["company_id"]
    )


def extract_year(value):
    """Extract a four-digit year from values such as Mar-2024."""

    extracted = (
        pd.Series([str(value)])
        .str.extract(r"(\d{4})", expand=False)
        .iloc[0]
    )

    if pd.isna(extracted):
        return np.nan

    return int(extracted)


def load_latest_fcf(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Load the latest available free cash flow for each company."""

    ratios = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            free_cash_flow_cr
        FROM financial_ratios
        """,
        connection,
    )

    ratios["company_id"] = (
        ratios["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    ratios["calendar_year"] = (
        ratios["year"]
        .apply(extract_year)
    )

    ratios["free_cash_flow_cr"] = pd.to_numeric(
        ratios["free_cash_flow_cr"],
        errors="coerce",
    )

    ratios = (
        ratios.dropna(
            subset=[
                "company_id",
                "calendar_year",
            ]
        )
        .sort_values(
            [
                "company_id",
                "calendar_year",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .drop_duplicates(
            subset=["company_id"],
            keep="first",
        )
    )

    return ratios[
        [
            "company_id",
            "free_cash_flow_cr",
        ]
    ]


def compute_five_year_median_pe(
    market_data: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate each company's median P/E over its latest five years."""

    records = []

    for company_id, group in market_data.groupby(
        "company_id"
    ):
        company_history = (
            group.sort_values(
                "year",
                ascending=False,
            )
            .drop_duplicates(
                subset=["year"],
                keep="first",
            )
            .head(5)
        )

        valid_pe = company_history.loc[
            company_history["pe_ratio"] > 0,
            "pe_ratio",
        ]

        median_pe = (
            valid_pe.median()
            if not valid_pe.empty
            else np.nan
        )

        records.append(
            {
                "company_id": company_id,
                "5yr_median_PE": median_pe,
            }
        )

    return pd.DataFrame(records)


def get_latest_market_records(
    market_data: pd.DataFrame,
) -> pd.DataFrame:
    """Keep the latest market-cap record for every company."""

    return (
        market_data.sort_values(
            [
                "company_id",
                "year",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .drop_duplicates(
            subset=["company_id"],
            keep="first",
        )
        .reset_index(drop=True)
    )


def assign_valuation_flag(row: pd.Series) -> str:
    """Assign Caution, Discount or Fair using sector median P/E."""

    pe_ratio = row["pe_ratio"]
    sector_median = row["sector_median_pe"]

    if (
        pd.isna(pe_ratio)
        or pd.isna(sector_median)
        or sector_median <= 0
        or pe_ratio <= 0
    ):
        return "Fair"

    if pe_ratio > sector_median * 1.5:
        return "Caution"

    if pe_ratio < sector_median * 0.7:
        return "Discount"

    return "Fair"


# ---------------------------------------------------------
# Valuation calculation
# ---------------------------------------------------------

def build_valuation_summary() -> pd.DataFrame:
    """Build the complete valuation output."""

    validate_files()

    market_data = load_market_cap_data()

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        companies = load_company_data(connection)
        sectors = load_sector_data(connection)
        latest_fcf = load_latest_fcf(connection)

    finally:
        connection.close()

    five_year_pe = compute_five_year_median_pe(
        market_data
    )

    latest_market = get_latest_market_records(
        market_data
    )

    valuation = (
        latest_market.merge(
            companies,
            on="company_id",
            how="left",
        )
        .merge(
            sectors,
            on="company_id",
            how="left",
        )
        .merge(
            latest_fcf,
            on="company_id",
            how="left",
        )
        .merge(
            five_year_pe,
            on="company_id",
            how="left",
        )
    )

    valuation["company_name"] = (
        valuation["company_name"]
        .fillna(valuation["company_id"])
    )

    valuation["broad_sector"] = (
        valuation["broad_sector"]
        .fillna("Unclassified")
    )

    # FCF Yield = FCF / Market Capitalisation × 100
    valuation["FCF_yield_pct"] = np.where(
        valuation["market_cap_crore"] > 0,
        (
            valuation["free_cash_flow_cr"]
            / valuation["market_cap_crore"]
        )
        * 100,
        np.nan,
    )

    # Sector median P/E using latest company records
    positive_pe_mask = valuation["pe_ratio"] > 0

    sector_medians = (
        valuation.loc[positive_pe_mask]
        .groupby("broad_sector")["pe_ratio"]
        .median()
        .rename("sector_median_pe")
        .reset_index()
    )

    valuation = valuation.merge(
        sector_medians,
        on="broad_sector",
        how="left",
    )

    # Difference from sector median as a percentage
    valuation["PE_vs_sector_median_pct"] = np.where(
        valuation["sector_median_pe"] > 0,
        (
            (
                valuation["pe_ratio"]
                - valuation["sector_median_pe"]
            )
            / valuation["sector_median_pe"]
        )
        * 100,
        np.nan,
    )

    valuation["flag"] = valuation.apply(
        assign_valuation_flag,
        axis=1,
    )

    summary = valuation.rename(
        columns={
            "broad_sector": "sector",
            "pe_ratio": "P/E",
            "pb_ratio": "P/B",
            "ev_ebitda": "EV/EBITDA",
        }
    )

    summary = summary[OUTPUT_COLUMNS].copy()

    numeric_columns = [
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
    ]

    summary[numeric_columns] = (
        summary[numeric_columns]
        .round(2)
    )

    summary = summary.sort_values(
        [
            "sector",
            "company_name",
        ]
    ).reset_index(drop=True)

    return summary


# ---------------------------------------------------------
# File export
# ---------------------------------------------------------

def export_valuation_files(
    summary: pd.DataFrame,
) -> None:
    """Export valuation summary and non-fair flags."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary.to_excel(
        SUMMARY_FILE,
        index=False,
    )

    valuation_flags = summary[
        summary["flag"].isin(
            [
                "Caution",
                "Discount",
            ]
        )
    ].copy()

    valuation_flags.to_csv(
        FLAGS_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\nValuation files generated successfully.")
    print(f"Summary file: {SUMMARY_FILE}")
    print(f"Flags file:   {FLAGS_FILE}")
    print(f"Summary rows: {len(summary)}")
    print(f"Flagged rows: {len(valuation_flags)}")

    print("\nFlag distribution:")
    print(
        summary["flag"]
        .value_counts(dropna=False)
        .to_string()
    )


def main() -> None:
    """Run the Day 26 valuation pipeline."""

    summary = build_valuation_summary()

    export_valuation_files(summary)

    print("\nFirst five valuation records:")
    print(summary.head().to_string(index=False))


if __name__ == "__main__":
    main()