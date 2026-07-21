import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_ratios, get_sectors


st.header("🏠 Home Dashboard")

selected_year = st.sidebar.selectbox(
    "Select Year",
    options=[2019, 2020, 2021, 2022, 2023, 2024],
    index=5,
)

ratios = get_ratios()
sectors = get_sectors()

if ratios.empty:
    st.warning("No financial ratio data is available.")
    st.stop()

ratios["calendar_year"] = (
    ratios["year"]
    .astype(str)
    .str.extract(r"(\d{4})", expand=False)
)

year_data = ratios[
    ratios["calendar_year"] == str(selected_year)
].copy()

if year_data.empty:
    st.warning(f"No data is available for {selected_year}.")
    st.stop()

# Keep one record per company for the selected year.
# Prefer Mar, then Jun, Sep, and Dec records.
month_priority = {
    "Mar": 1,
    "Jun": 2,
    "Sep": 3,
    "Dec": 4,
}

year_data["month_name"] = (
    year_data["year"]
    .astype(str)
    .str.extract(r"^(Mar|Jun|Sep|Dec)", expand=False)
)

year_data["month_priority"] = (
    year_data["month_name"]
    .map(month_priority)
    .fillna(0)
)

year_data = (
    year_data
    .sort_values(
        ["company_id", "month_priority"],
        ascending=[True, False],
    )
    .drop_duplicates(subset=["company_id"], keep="first")
)

for column in [
    "return_on_equity_pct",
    "roe",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "composite_quality_score",
]:
    if column in year_data.columns:
        year_data[column] = pd.to_numeric(
            year_data[column],
            errors="coerce",
        )

roe_column = (
    "return_on_equity_pct"
    if "return_on_equity_pct" in year_data.columns
    else "roe"
)

average_roe = year_data[roe_column].mean()
median_de = year_data["debt_to_equity"].median()
total_companies = year_data["company_id"].nunique()
median_revenue_cagr = year_data["revenue_cagr_5yr"].median()

debt_free_count = year_data[
    year_data["debt_to_equity"].fillna(float("inf")) <= 0.10
]["company_id"].nunique()

# P/E is not currently available in financial_ratios.
median_pe = None

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Average ROE",
        f"{average_roe:.2f}%" if pd.notna(average_roe) else "N/A",
    )

with col2:
    st.metric(
        "Median P/E",
        "N/A",
        help="P/E data is not currently available in the database.",
    )

with col3:
    st.metric(
        "Median D/E",
        f"{median_de:.2f}" if pd.notna(median_de) else "N/A",
    )

col4, col5, col6 = st.columns(3)

with col4:
    st.metric("Total Companies", int(total_companies))

with col5:
    st.metric(
        "Median Revenue CAGR 5yr",
        (
            f"{median_revenue_cagr:.2f}%"
            if pd.notna(median_revenue_cagr)
            else "N/A"
        ),
    )

with col6:
    st.metric("Debt-Free Companies", int(debt_free_count))

st.divider()

left, right = st.columns([1.25, 1])

with left:
    st.subheader("Sector Breakdown")

    sector_counts = (
        sectors.dropna(subset=["broad_sector"])
        .groupby("broad_sector", as_index=False)
        .agg(company_count=("company_id", "nunique"))
        .sort_values("company_count", ascending=False)
    )

    if sector_counts.empty:
        st.info("Sector data is not available.")
    else:
        donut = px.pie(
            sector_counts,
            names="broad_sector",
            values="company_count",
            hole=0.55,
            title=f"Companies by Sector — {selected_year}",
        )

        donut.update_traces(
            textposition="inside",
            textinfo="percent+label",
        )

        donut.update_layout(
            legend_title_text="Sector",
            margin=dict(l=10, r=10, t=60, b=10),
        )

        st.plotly_chart(
            donut,
            use_container_width=True,
        )

with right:
    st.subheader("Top 5 Companies by Quality Score")

    top_columns = [
        "company_name",
        "broad_sector",
        "composite_quality_score",
        roe_column,
        "debt_to_equity",
        "revenue_cagr_5yr",
    ]

    available_columns = [
        column
        for column in top_columns
        if column in year_data.columns
    ]

    top_five = (
        year_data.dropna(subset=["composite_quality_score"])
        .sort_values(
            "composite_quality_score",
            ascending=False,
        )
        .head(5)[available_columns]
        .copy()
    )

    rename_map = {
        "company_name": "Company",
        "broad_sector": "Sector",
        "composite_quality_score": "Quality Score",
        roe_column: "ROE %",
        "debt_to_equity": "D/E",
        "revenue_cagr_5yr": "Revenue CAGR 5yr %",
    }

    top_five = top_five.rename(columns=rename_map)

    numeric_columns = top_five.select_dtypes(
        include="number"
    ).columns

    top_five[numeric_columns] = top_five[
        numeric_columns
    ].round(2)

    if top_five.empty:
        st.info(
            f"No composite quality-score data is available for {selected_year}."
        )
    else:
        st.dataframe(
            top_five,
            use_container_width=True,
            hide_index=True,
        )

st.caption(
    "Median P/E is shown as N/A because the current database does not contain P/E data."
)