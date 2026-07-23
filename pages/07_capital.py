import re

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_connection


st.header("💰 Capital Allocation")
st.caption(
    "Analyse how companies generate and allocate cash across "
    "operations, investment, debt and dividends."
)


def extract_calendar_year(value):
    """Extract a four-digit calendar year."""
    match = re.search(r"\d{4}", str(value))

    if match:
        return int(match.group())

    return None


def keep_latest_annual_record(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Keep the latest annual record for every company."""
    if dataframe.empty:
        return dataframe

    result = dataframe.copy()

    result["calendar_year"] = (
        result["year"]
        .apply(extract_calendar_year)
    )

    result["month_name"] = (
        result["year"]
        .astype(str)
        .str.extract(
            r"^(Mar|Jun|Sep|Dec)",
            expand=False,
        )
    )

    month_priority = {
        "Mar": 4,
        "Jun": 3,
        "Sep": 2,
        "Dec": 1,
    }

    result["month_priority"] = (
        result["month_name"]
        .map(month_priority)
        .fillna(0)
    )

    return (
        result.dropna(subset=["calendar_year"])
        .sort_values(
            [
                "company_id",
                "calendar_year",
                "month_priority",
            ],
            ascending=[
                True,
                False,
                False,
            ],
        )
        .drop_duplicates(
            subset=["company_id"],
            keep="first",
        )
        .reset_index(drop=True)
    )


@st.cache_data
def load_capital_data() -> pd.DataFrame:
    """Load latest capital-allocation data from SQLite."""
    connection = get_connection()

    try:
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
                broad_sector,
                sub_sector
            FROM sectors
            """,
            connection,
        )

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                free_cash_flow_cr,
                capex_cr,
                total_debt_cr,
                cash_from_operations_cr,
                dividend_payout_ratio_pct,
                fcf_conversion_rate_pct,
                composite_quality_score
            FROM financial_ratios
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

    finally:
        connection.close()

    latest_ratios = keep_latest_annual_record(ratios)
    latest_cashflow = keep_latest_annual_record(cashflow)

    latest_ratios = latest_ratios[
        [
            "company_id",
            "calendar_year",
            "free_cash_flow_cr",
            "capex_cr",
            "total_debt_cr",
            "cash_from_operations_cr",
            "dividend_payout_ratio_pct",
            "fcf_conversion_rate_pct",
            "composite_quality_score",
        ]
    ].rename(
        columns={
            "calendar_year": "ratio_year",
        }
    )

    latest_cashflow = latest_cashflow[
        [
            "company_id",
            "calendar_year",
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ]
    ].rename(
        columns={
            "calendar_year": "cashflow_year",
        }
    )

    for dataframe in [
        companies,
        sectors,
        latest_ratios,
        latest_cashflow,
    ]:
        dataframe["company_id"] = (
            dataframe["company_id"]
            .astype(str)
        )

    dataset = (
        companies.merge(
            sectors,
            on="company_id",
            how="left",
        )
        .merge(
            latest_ratios,
            on="company_id",
            how="left",
        )
        .merge(
            latest_cashflow,
            on="company_id",
            how="left",
        )
    )

    numeric_columns = [
        "free_cash_flow_cr",
        "capex_cr",
        "total_debt_cr",
        "cash_from_operations_cr",
        "dividend_payout_ratio_pct",
        "fcf_conversion_rate_pct",
        "composite_quality_score",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    for column in numeric_columns:
        dataset[column] = pd.to_numeric(
            dataset[column],
            errors="coerce",
        )

    dataset["broad_sector"] = (
        dataset["broad_sector"]
        .fillna("Unclassified")
    )

    dataset["sub_sector"] = (
        dataset["sub_sector"]
        .fillna("Not Available")
    )

    return dataset


def classify_pattern(row: pd.Series) -> str:
    """
    Classify each company using available cash-flow metrics.

    These labels are analytical indicators, not investment advice.
    """
    cfo = row.get("cash_from_operations_cr")
    fcf = row.get("free_cash_flow_cr")
    capex = row.get("capex_cr")
    debt = row.get("total_debt_cr")
    payout = row.get("dividend_payout_ratio_pct")

    if pd.notna(cfo) and cfo < 0:
        return "Cash Flow Pressure"

    if (
        pd.notna(fcf)
        and fcf > 0
        and pd.notna(payout)
        and payout >= 30
    ):
        return "Shareholder Returns"

    if (
        pd.notna(cfo)
        and cfo > 0
        and pd.notna(capex)
        and abs(capex) >= abs(cfo) * 0.50
    ):
        return "Growth Reinvestment"

    if (
        pd.notna(fcf)
        and fcf > 0
        and (
            pd.isna(debt)
            or debt <= abs(fcf) * 2
        )
    ):
        return "Cash Generator"

    if (
        pd.notna(debt)
        and debt > 0
        and (
            pd.isna(fcf)
            or fcf <= 0
        )
    ):
        return "Debt-Dependent"

    return "Balanced / Unclear"


data = load_capital_data()


if data.empty:
    st.warning("Capital-allocation data is not available.")
    st.stop()


data["Allocation Pattern"] = data.apply(
    classify_pattern,
    axis=1,
)


sector_options = ["All Sectors"] + sorted(
    data["broad_sector"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


selected_sector = st.selectbox(
    "Filter by Sector",
    sector_options,
)


if selected_sector == "All Sectors":
    filtered_data = data.copy()
else:
    filtered_data = data[
        data["broad_sector"] == selected_sector
    ].copy()


if filtered_data.empty:
    st.info(
        "No capital-allocation records are available "
        "for the selected sector."
    )
    st.stop()


company_count = filtered_data[
    "company_id"
].nunique()

positive_fcf_count = (
    filtered_data["free_cash_flow_cr"] > 0
).sum()

median_cfo = filtered_data[
    "cash_from_operations_cr"
].median()

median_fcf = filtered_data[
    "free_cash_flow_cr"
].median()


summary_columns = st.columns(4)

summary_columns[0].metric(
    "Companies",
    f"{company_count}",
)

summary_columns[1].metric(
    "Positive FCF Companies",
    f"{positive_fcf_count}",
)

summary_columns[2].metric(
    "Median CFO",
    (
        f"₹{median_cfo:,.2f} Cr"
        if pd.notna(median_cfo)
        else "N/A"
    ),
)

summary_columns[3].metric(
    "Median FCF",
    (
        f"₹{median_fcf:,.2f} Cr"
        if pd.notna(median_fcf)
        else "N/A"
    ),
)


st.subheader("Capital Allocation Treemap")


treemap_data = filtered_data.copy()

treemap_data["treemap_value"] = (
    treemap_data["cash_from_operations_cr"]
    .abs()
)

treemap_data["treemap_value"] = (
    treemap_data["treemap_value"]
    .fillna(
        treemap_data["free_cash_flow_cr"].abs()
    )
    .fillna(
        treemap_data["net_cash_flow"].abs()
    )
    .fillna(1)
    .clip(lower=1)
)


treemap_chart = px.treemap(
    treemap_data,
    path=[
        px.Constant("Nifty 100"),
        "Allocation Pattern",
        "broad_sector",
        "company_name",
    ],
    values="treemap_value",
    hover_data={
        "sub_sector": True,
        "cash_from_operations_cr": ":,.2f",
        "free_cash_flow_cr": ":,.2f",
        "capex_cr": ":,.2f",
        "total_debt_cr": ":,.2f",
        "dividend_payout_ratio_pct": ":.2f",
        "treemap_value": False,
    },
    labels={
        "cash_from_operations_cr": "Cash from Operations ₹ Cr",
        "free_cash_flow_cr": "Free Cash Flow ₹ Cr",
        "capex_cr": "Capex ₹ Cr",
        "total_debt_cr": "Total Debt ₹ Cr",
        "dividend_payout_ratio_pct": "Dividend Payout %",
        "broad_sector": "Sector",
        "sub_sector": "Sub-sector",
    },
)


treemap_chart.update_layout(
    margin={
        "l": 10,
        "r": 10,
        "t": 30,
        "b": 10,
    }
)


st.plotly_chart(
    treemap_chart,
    width="stretch",
)


st.caption(
    "Treemap size uses absolute cash from operations. "
    "Free cash flow or net cash flow is used when CFO is unavailable."
)


st.subheader("Allocation Pattern Distribution")


pattern_summary = (
    filtered_data.groupby(
        "Allocation Pattern",
        as_index=False,
    )
    .agg(
        Companies=("company_id", "nunique"),
        Median_CFO=(
            "cash_from_operations_cr",
            "median",
        ),
        Median_FCF=(
            "free_cash_flow_cr",
            "median",
        ),
        Median_Debt=(
            "total_debt_cr",
            "median",
        ),
    )
    .sort_values(
        "Companies",
        ascending=False,
    )
)


pattern_chart = px.bar(
    pattern_summary,
    x="Allocation Pattern",
    y="Companies",
    text_auto=True,
    hover_data={
        "Median_CFO": ":,.2f",
        "Median_FCF": ":,.2f",
        "Median_Debt": ":,.2f",
    },
)


pattern_chart.update_layout(
    xaxis_title="",
    yaxis_title="Number of Companies",
    margin={
        "l": 20,
        "r": 20,
        "t": 20,
        "b": 20,
    },
)


st.plotly_chart(
    pattern_chart,
    width="stretch",
)


st.subheader("Company Capital Allocation Table")


pattern_filter = st.multiselect(
    "Filter Allocation Pattern",
    options=sorted(
        filtered_data[
            "Allocation Pattern"
        ].unique()
    ),
    default=sorted(
        filtered_data[
            "Allocation Pattern"
        ].unique()
    ),
)


if pattern_filter:
    table_data = filtered_data[
        filtered_data["Allocation Pattern"].isin(
            pattern_filter
        )
    ].copy()
else:
    table_data = filtered_data.iloc[0:0].copy()


display_columns = {
    "company_name": "Company",
    "broad_sector": "Sector",
    "sub_sector": "Sub-sector",
    "ratio_year": "Financial Year",
    "Allocation Pattern": "Allocation Pattern",
    "cash_from_operations_cr": "Cash from Operations ₹ Cr",
    "free_cash_flow_cr": "Free Cash Flow ₹ Cr",
    "capex_cr": "Capex ₹ Cr",
    "total_debt_cr": "Total Debt ₹ Cr",
    "dividend_payout_ratio_pct": "Dividend Payout %",
    "fcf_conversion_rate_pct": "FCF Conversion %",
    "net_cash_flow": "Net Cash Flow ₹ Cr",
    "composite_quality_score": "Quality Score",
}


available_columns = [
    column
    for column in display_columns
    if column in table_data.columns
]


company_table = (
    table_data[available_columns]
    .rename(columns=display_columns)
    .sort_values(
        by="Free Cash Flow ₹ Cr",
        ascending=False,
        na_position="last",
    )
    .reset_index(drop=True)
)


numeric_columns = company_table.select_dtypes(
    include="number"
).columns

company_table[numeric_columns] = (
    company_table[numeric_columns]
    .round(2)
)


st.dataframe(
    company_table,
    width="stretch",
    hide_index=True,
)


csv_data = company_table.to_csv(
    index=False
).encode("utf-8")


st.download_button(
    label="Download Capital Allocation Data",
    data=csv_data,
    file_name="capital_allocation_analysis.csv",
    mime="text/csv",
)


st.info(
    "Allocation patterns are rule-based analytical labels created "
    "from the available financial data. They should not be treated "
    "as investment recommendations."
)