import re

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_connection


st.header("🏭 Sector Analysis")
st.caption(
    "Compare companies and financial performance within each sector."
)


def extract_calendar_year(value):
    """Extract the four-digit year from values such as Mar-2025."""
    match = re.search(r"\d{4}", str(value))

    if match:
        return int(match.group())

    return None


def keep_latest_annual_record(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep the latest annual record for each company.

    If multiple records exist for the same year, March receives
    the highest priority.
    """
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

    result = (
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

    return result


@st.cache_data
def load_sector_dataset() -> pd.DataFrame:
    """Load companies, sectors and latest financial information."""
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
                roe,
                debt_to_equity,
                net_profit_margin_pct,
                operating_profit_margin_pct,
                asset_turnover,
                free_cash_flow_cr,
                revenue_cagr_5yr,
                pat_cagr_5yr,
                composite_quality_score
            FROM financial_ratios
            """,
            connection,
        )

        profit_loss = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                sales,
                operating_profit,
                net_profit,
                eps
            FROM profitandloss
            """,
            connection,
        )

    finally:
        connection.close()

    latest_ratios = keep_latest_annual_record(ratios)
    latest_profit_loss = keep_latest_annual_record(
        profit_loss
    )

    ratio_columns = [
        "company_id",
        "calendar_year",
        "roe",
        "debt_to_equity",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "asset_turnover",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "composite_quality_score",
    ]

    profit_loss_columns = [
        "company_id",
        "calendar_year",
        "sales",
        "operating_profit",
        "net_profit",
        "eps",
    ]

    latest_ratios = latest_ratios[
        [
            column
            for column in ratio_columns
            if column in latest_ratios.columns
        ]
    ].rename(
        columns={
            "calendar_year": "ratio_year",
        }
    )

    latest_profit_loss = latest_profit_loss[
        [
            column
            for column in profit_loss_columns
            if column in latest_profit_loss.columns
        ]
    ].rename(
        columns={
            "calendar_year": "financial_year",
        }
    )

    for dataframe in [
        companies,
        sectors,
        latest_ratios,
        latest_profit_loss,
    ]:
        if "company_id" in dataframe.columns:
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
            latest_profit_loss,
            on="company_id",
            how="left",
        )
    )

    numeric_columns = [
        "roe",
        "debt_to_equity",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "asset_turnover",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "composite_quality_score",
        "sales",
        "operating_profit",
        "net_profit",
        "eps",
    ]

    for column in numeric_columns:
        if column in dataset.columns:
            dataset[column] = pd.to_numeric(
                dataset[column],
                errors="coerce",
            )

    dataset["broad_sector"] = (
        dataset["broad_sector"]
        .fillna("Unclassified")
        .astype(str)
    )

    dataset["sub_sector"] = (
        dataset["sub_sector"]
        .fillna("Not Available")
        .astype(str)
    )

    return dataset


data = load_sector_dataset()


if data.empty:
    st.warning("Sector data is not available.")
    st.stop()


sector_options = sorted(
    [
        sector
        for sector in data["broad_sector"].dropna().unique()
        if str(sector).strip()
    ]
)


if not sector_options:
    st.warning("No sector classifications are available.")
    st.stop()


selected_sector = st.selectbox(
    "Select Sector",
    sector_options,
)


sector_data = data[
    data["broad_sector"] == selected_sector
].copy()


if sector_data.empty:
    st.info(
        "No companies are available for the selected sector."
    )
    st.stop()


st.subheader(selected_sector)


company_count = sector_data[
    "company_id"
].nunique()

median_revenue = sector_data[
    "sales"
].median()

median_roe = sector_data[
    "roe"
].median()

median_margin = sector_data[
    "net_profit_margin_pct"
].median()


metric_columns = st.columns(4)

metric_columns[0].metric(
    "Companies",
    f"{company_count}",
)

metric_columns[1].metric(
    "Median Revenue",
    (
        f"₹{median_revenue:,.2f} Cr"
        if pd.notna(median_revenue)
        else "N/A"
    ),
)

metric_columns[2].metric(
    "Median ROE",
    (
        f"{median_roe:.2f}%"
        if pd.notna(median_roe)
        else "N/A"
    ),
)

metric_columns[3].metric(
    "Median Net Margin",
    (
        f"{median_margin:.2f}%"
        if pd.notna(median_margin)
        else "N/A"
    ),
)


st.subheader("Company Performance Map")

st.caption(
    "Revenue is shown on the horizontal axis and ROE on the "
    "vertical axis. Bubble size uses absolute free cash flow. "
    "When free cash flow is unavailable, absolute net profit "
    "is used."
)


bubble_data = sector_data.copy()

bubble_data["bubble_size"] = (
    bubble_data["free_cash_flow_cr"].abs()
)

bubble_data["bubble_size"] = (
    bubble_data["bubble_size"]
    .fillna(
        bubble_data["net_profit"].abs()
    )
)

bubble_data["bubble_size"] = (
    bubble_data["bubble_size"]
    .fillna(1)
    .clip(lower=1)
)


bubble_data = bubble_data.dropna(
    subset=[
        "sales",
        "roe",
    ]
)


if bubble_data.empty:
    st.info(
        "Revenue and ROE data are not available for enough "
        "companies to create the bubble chart."
    )
else:
    bubble_chart = px.scatter(
        bubble_data,
        x="sales",
        y="roe",
        size="bubble_size",
        hover_name="company_name",
        hover_data={
            "sub_sector": True,
            "sales": ":,.2f",
            "roe": ":.2f",
            "net_profit": ":,.2f",
            "free_cash_flow_cr": ":,.2f",
            "bubble_size": False,
        },
        labels={
            "sales": "Revenue ₹ Cr",
            "roe": "ROE %",
            "sub_sector": "Sub-sector",
            "net_profit": "Net Profit ₹ Cr",
            "free_cash_flow_cr": "Free Cash Flow ₹ Cr",
        },
        size_max=55,
    )

    bubble_chart.update_layout(
        xaxis_title="Revenue ₹ Cr",
        yaxis_title="ROE %",
        margin={
            "l": 20,
            "r": 20,
            "t": 30,
            "b": 20,
        },
    )

    st.plotly_chart(
        bubble_chart,
        width="stretch",
    )


st.subheader("Sector Median KPIs")


kpi_mapping = {
    "ROE %": "roe",
    "Debt-to-Equity": "debt_to_equity",
    "Net Profit Margin %": "net_profit_margin_pct",
    "Operating Margin %": (
        "operating_profit_margin_pct"
    ),
    "Asset Turnover": "asset_turnover",
    "Revenue CAGR 5yr %": "revenue_cagr_5yr",
    "PAT CAGR 5yr %": "pat_cagr_5yr",
    "Quality Score": "composite_quality_score",
}


median_rows = []

for display_name, column_name in kpi_mapping.items():

    if column_name not in sector_data.columns:
        continue

    median_value = sector_data[column_name].median()

    if pd.notna(median_value):
        median_rows.append(
            {
                "KPI": display_name,
                "Median Value": median_value,
            }
        )


median_kpi_data = pd.DataFrame(median_rows)


if median_kpi_data.empty:
    st.info(
        "Median KPI data is not available for this sector."
    )
else:
    median_chart = px.bar(
        median_kpi_data,
        x="KPI",
        y="Median Value",
        text_auto=".2f",
        labels={
            "Median Value": "Sector Median",
        },
    )

    median_chart.update_layout(
        xaxis_title="",
        yaxis_title="Median Value",
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
    )

    st.plotly_chart(
        median_chart,
        width="stretch",
    )


st.subheader("Companies in Selected Sector")


display_columns = {
    "company_name": "Company",
    "sub_sector": "Sub-sector",
    "financial_year": "Financial Year",
    "sales": "Revenue ₹ Cr",
    "net_profit": "Net Profit ₹ Cr",
    "roe": "ROE %",
    "debt_to_equity": "Debt-to-Equity",
    "net_profit_margin_pct": "Net Margin %",
    "operating_profit_margin_pct": "OPM %",
    "free_cash_flow_cr": "Free Cash Flow ₹ Cr",
    "revenue_cagr_5yr": "Revenue CAGR 5yr %",
    "pat_cagr_5yr": "PAT CAGR 5yr %",
    "composite_quality_score": "Quality Score",
}


available_display_columns = [
    column
    for column in display_columns
    if column in sector_data.columns
]


company_table = (
    sector_data[available_display_columns]
    .rename(columns=display_columns)
    .sort_values(
        by="Revenue ₹ Cr",
        ascending=False,
        na_position="last",
    )
    .reset_index(drop=True)
)


numeric_table_columns = company_table.select_dtypes(
    include="number"
).columns

company_table[numeric_table_columns] = (
    company_table[numeric_table_columns]
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
    label="Download Sector Data as CSV",
    data=csv_data,
    file_name=(
        selected_sector.lower()
        .replace(" ", "_")
        .replace("/", "_")
        + "_sector_analysis.csv"
    ),
    mime="text/csv",
)


st.caption(
    "Market-cap data is not currently present in the database, "
    "so free cash flow or net profit is used for bubble size."
)