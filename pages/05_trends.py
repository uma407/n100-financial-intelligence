import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_pl,
    get_ratios,
)


st.header("📈 Trend Analysis")
st.caption(
    "Compare up to three financial metrics across the latest "
    "10 available years."
)


def extract_calendar_year(value):
    """Extract a four-digit calendar year."""
    match = re.search(r"\d{4}", str(value))

    if match:
        return int(match.group())

    return None


def prepare_annual_data(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep one record per calendar year.

    March is preferred because most complete annual data is
    stored in March rows.
    """
    if dataframe.empty:
        return dataframe

    result = dataframe.copy()

    result["calendar_year"] = (
        result["year"]
        .apply(extract_calendar_year)
    )

    month_priority = {
        "Mar": 4,
        "Jun": 3,
        "Sep": 2,
        "Dec": 1,
    }

    result["month_name"] = (
        result["year"]
        .astype(str)
        .str.extract(
            r"^(Mar|Jun|Sep|Dec)",
            expand=False,
        )
    )

    result["month_priority"] = (
        result["month_name"]
        .map(month_priority)
        .fillna(0)
    )

    result = (
        result.dropna(
            subset=["calendar_year"]
        )
        .sort_values(
            [
                "calendar_year",
                "month_priority",
            ],
            ascending=[True, False],
        )
        .drop_duplicates(
            subset=["calendar_year"],
            keep="first",
        )
        .tail(10)
        .reset_index(drop=True)
    )

    return result


companies = get_companies()

if companies.empty:
    st.warning("Company data is not available.")
    st.stop()


companies = companies.copy()

companies["company_name"] = (
    companies["company_name"]
    .fillna("Unknown Company")
    .astype(str)
)

companies["id"] = (
    companies["id"]
    .astype(str)
)

companies["search_label"] = (
    companies["company_name"]
    + " — "
    + companies["id"]
)


search_text = st.text_input(
    "Search company name or ticker",
    placeholder="Example: TCS, Infosys, Reliance...",
).strip()


if search_text:
    matching_companies = companies[
        companies["company_name"]
        .str.contains(
            search_text,
            case=False,
            na=False,
        )
        |
        companies["id"]
        .str.contains(
            search_text,
            case=False,
            na=False,
        )
    ].copy()
else:
    matching_companies = companies.copy()


if matching_companies.empty:
    st.warning(
        "Ticker not found — please try another."
    )
    st.stop()


selected_label = st.selectbox(
    "Select Company",
    options=matching_companies[
        "search_label"
    ].tolist(),
)


selected_company = matching_companies[
    matching_companies["search_label"]
    == selected_label
].iloc[0]


company_id = selected_company["id"]
company_name = selected_company["company_name"]


ratio_data = prepare_annual_data(
    get_ratios(company_id)
)

pl_data = prepare_annual_data(
    get_pl(company_id)
)


if ratio_data.empty and pl_data.empty:
    st.info(
        "Financial trend data is not available "
        "for this company."
    )
    st.stop()


metric_sources = {
    "Revenue ₹ Cr": (
        pl_data,
        "sales",
    ),
    "Net Profit ₹ Cr": (
        pl_data,
        "net_profit",
    ),
    "Operating Profit ₹ Cr": (
        pl_data,
        "operating_profit",
    ),
    "EPS": (
        pl_data,
        "eps",
    ),
    "ROE %": (
        ratio_data,
        "roe",
    ),
    "Net Profit Margin %": (
        ratio_data,
        "net_profit_margin_pct",
    ),
    "Operating Profit Margin %": (
        ratio_data,
        "operating_profit_margin_pct",
    ),
    "Debt-to-Equity": (
        ratio_data,
        "debt_to_equity",
    ),
    "Free Cash Flow ₹ Cr": (
        ratio_data,
        "free_cash_flow_cr",
    ),
    "Asset Turnover": (
        ratio_data,
        "asset_turnover",
    ),
    "Revenue CAGR 5yr %": (
        ratio_data,
        "revenue_cagr_5yr",
    ),
    "PAT CAGR 5yr %": (
        ratio_data,
        "pat_cagr_5yr",
    ),
    "EPS CAGR 5yr %": (
        ratio_data,
        "eps_cagr_5yr",
    ),
    "Quality Score": (
        ratio_data,
        "composite_quality_score",
    ),
}


available_metrics = []

for metric_name, (
    source_dataframe,
    source_column,
) in metric_sources.items():

    if source_dataframe.empty:
        continue

    if source_column not in source_dataframe.columns:
        continue

    numeric_values = pd.to_numeric(
        source_dataframe[source_column],
        errors="coerce",
    )

    if numeric_values.notna().any():
        available_metrics.append(metric_name)


if not available_metrics:
    st.warning(
        "No numeric trend metrics are available "
        "for this company."
    )
    st.stop()


default_metrics = [
    metric
    for metric in [
        "Revenue ₹ Cr",
        "Net Profit ₹ Cr",
        "ROE %",
    ]
    if metric in available_metrics
]


if not default_metrics:
    default_metrics = available_metrics[:1]


selected_metrics = st.multiselect(
    "Select up to 3 metrics",
    options=available_metrics,
    default=default_metrics[:3],
    max_selections=3,
)


if not selected_metrics:
    st.info(
        "Select at least one metric to display the trend."
    )
    st.stop()


st.subheader(
    f"{company_name} — 10-Year Financial Trend"
)


chart = go.Figure()


for metric_name in selected_metrics:

    source_dataframe, source_column = (
        metric_sources[metric_name]
    )

    metric_data = source_dataframe[
        [
            "calendar_year",
            source_column,
        ]
    ].copy()

    metric_data[source_column] = pd.to_numeric(
        metric_data[source_column],
        errors="coerce",
    )

    metric_data = (
        metric_data.dropna(
            subset=[
                "calendar_year",
                source_column,
            ]
        )
        .sort_values("calendar_year")
        .tail(10)
    )

    if metric_data.empty:
        continue

    metric_data["yoy_change_pct"] = (
        metric_data[source_column]
        .pct_change()
        .mul(100)
    )

    annotation_text = []

    for yoy_value in metric_data[
        "yoy_change_pct"
    ]:

        if pd.isna(yoy_value):
            annotation_text.append("")
        else:
            annotation_text.append(
                f"{yoy_value:+.1f}%"
            )

    chart.add_trace(
        go.Scatter(
            x=metric_data["calendar_year"],
            y=metric_data[source_column],
            mode="lines+markers+text",
            name=metric_name,
            text=annotation_text,
            textposition="top center",
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "Year: %{x}<br>"
                "Value: %{y:,.2f}<br>"
                "YoY: %{text}<extra></extra>"
            ),
        )
    )


if not chart.data:
    st.info(
        "The selected metrics have no usable values."
    )
    st.stop()


chart.update_layout(
    xaxis_title="Year",
    yaxis_title="Metric Value",
    hovermode="x unified",
    legend_title="Metric",
    margin={
        "l": 20,
        "r": 20,
        "t": 40,
        "b": 20,
    },
)

chart.update_xaxes(
    dtick=1,
    tickmode="linear",
)

st.plotly_chart(
    chart,
    width="stretch",
)


st.subheader("Trend Data")

merged_table = None


for metric_name in selected_metrics:

    source_dataframe, source_column = (
        metric_sources[metric_name]
    )

    metric_table = source_dataframe[
        [
            "calendar_year",
            source_column,
        ]
    ].copy()

    metric_table[source_column] = pd.to_numeric(
        metric_table[source_column],
        errors="coerce",
    )

    metric_table = (
        metric_table.dropna(
            subset=["calendar_year"]
        )
        .sort_values("calendar_year")
        .drop_duplicates(
            subset=["calendar_year"],
            keep="first",
        )
        .tail(10)
        .rename(
            columns={
                source_column: metric_name,
            }
        )
    )

    if merged_table is None:
        merged_table = metric_table
    else:
        merged_table = merged_table.merge(
            metric_table,
            on="calendar_year",
            how="outer",
        )


if merged_table is not None:

    merged_table = (
        merged_table
        .sort_values("calendar_year")
        .rename(
            columns={
                "calendar_year": "Year",
            }
        )
    )

    numeric_columns = merged_table.select_dtypes(
        include="number"
    ).columns

    merged_table[numeric_columns] = (
        merged_table[numeric_columns]
        .round(2)
    )

    st.dataframe(
        merged_table,
        width="stretch",
        hide_index=True,
    )


available_year_count = max(
    len(ratio_data),
    len(pl_data),
)


if available_year_count < 10:
    st.caption(
        f"Only {available_year_count} years of usable "
        "data are available for this company."
    )
else:
    st.caption(
        "The chart displays the latest 10 available years. "
        "YoY labels show percentage change from the "
        "previous available year."
    )