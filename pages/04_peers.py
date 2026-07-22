import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_peers, get_ratios


st.header("👥 Peer Comparison")
st.caption(
    "Compare a company with other businesses in the same peer group."
)


@st.cache_data(ttl=600)
def load_latest_ratios() -> pd.DataFrame:
    """Return the latest annual ratio record for every company."""
    data = get_ratios()

    if data.empty:
        return data

    data = data.copy()

    data["calendar_year"] = (
        data["year"]
        .astype(str)
        .str.extract(r"(\d{4})", expand=False)
    )

    data["calendar_year_number"] = pd.to_numeric(
        data["calendar_year"],
        errors="coerce",
    )

    month_priority = {
        "Mar": 4,
        "Jun": 3,
        "Sep": 2,
        "Dec": 1,
    }

    data["month_name"] = (
        data["year"]
        .astype(str)
        .str.extract(
            r"^(Mar|Jun|Sep|Dec)",
            expand=False,
        )
    )

    data["month_priority"] = (
        data["month_name"]
        .map(month_priority)
        .fillna(0)
    )

    data = (
        data.sort_values(
            [
                "company_id",
                "calendar_year_number",
                "month_priority",
            ],
            ascending=[True, False, False],
        )
        .drop_duplicates(
            subset=["company_id"],
            keep="first",
        )
        .reset_index(drop=True)
    )

    numeric_columns = [
        "roe",
        "return_on_equity_pct",
        "debt_to_equity",
        "net_profit_margin",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "asset_turnover",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

    data["roe_display"] = pd.to_numeric(
        data.get(
            "return_on_equity_pct",
            pd.Series(index=data.index, dtype=float),
        ),
        errors="coerce",
    )

    if "roe" in data.columns:
        data["roe_display"] = (
            data["roe_display"]
            .fillna(data["roe"])
        )

    data["npm_display"] = pd.to_numeric(
        data.get(
            "net_profit_margin_pct",
            pd.Series(index=data.index, dtype=float),
        ),
        errors="coerce",
    )

    if "net_profit_margin" in data.columns:
        data["npm_display"] = (
            data["npm_display"]
            .fillna(data["net_profit_margin"])
        )

    return data


peer_data = get_peers()
ratio_data = load_latest_ratios()

if peer_data.empty:
    st.warning("Peer-group data is not available.")
    st.stop()

if ratio_data.empty:
    st.warning("Financial-ratio data is not available.")
    st.stop()


peer_data = peer_data.copy()

peer_data["peer_group_name"] = (
    peer_data["peer_group_name"]
    .fillna("No peer group assigned")
    .astype(str)
    .str.strip()
)

group_names = sorted(
    peer_data.loc[
        peer_data["peer_group_name"]
        != "No peer group assigned",
        "peer_group_name",
    ]
    .dropna()
    .unique()
    .tolist()
)

if not group_names:
    st.warning("No valid peer groups are available.")
    st.stop()


selected_group = st.selectbox(
    "Select Peer Group",
    options=group_names,
)

selected_peers = peer_data[
    peer_data["peer_group_name"] == selected_group
].copy()

selected_peers["company_id"] = (
    selected_peers["company_id"]
    .astype(str)
)

ratio_data["company_id"] = (
    ratio_data["company_id"]
    .astype(str)
)

comparison = selected_peers.merge(
    ratio_data,
    on="company_id",
    how="left",
    suffixes=("_peer", ""),
)

if comparison.empty:
    st.info(
        "No companies are available for this peer group."
    )
    st.stop()


comparison["display_name"] = (
    comparison["company_name_peer"]
    .fillna(comparison["company_name"])
    .fillna(comparison["company_id"])
)

company_options = (
    comparison[
        ["company_id", "display_name"]
    ]
    .drop_duplicates()
    .sort_values("display_name")
)

company_labels = {
    row["display_name"]: row["company_id"]
    for _, row in company_options.iterrows()
}

selected_company_name = st.selectbox(
    "Select Benchmark Company",
    options=list(company_labels.keys()),
)

selected_company_id = company_labels[
    selected_company_name
]


metric_map = {
    "ROE %": "roe_display",
    "Net Profit Margin %": "npm_display",
    "Operating Margin %": "operating_profit_margin_pct",
    "Revenue CAGR 5yr %": "revenue_cagr_5yr",
    "PAT CAGR 5yr %": "pat_cagr_5yr",
    "Asset Turnover": "asset_turnover",
    "Free Cash Flow ₹ Cr": "free_cash_flow_cr",
    "Quality Score": "composite_quality_score",
}

available_metrics = {
    label: column
    for label, column in metric_map.items()
    if (
        column in comparison.columns
        and comparison[column].notna().any()
    )
}

if not available_metrics:
    st.warning(
        "No comparable financial metrics are available "
        "for this peer group."
    )
    st.stop()


def percentile_score(
    series: pd.Series,
    value: float,
    higher_is_better: bool = True,
) -> float:
    """
    Convert a raw metric value to a 0–100 peer percentile.
    """
    numeric = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if numeric.empty or pd.isna(value):
        return 0.0

    if len(numeric) == 1:
        return 50.0

    if higher_is_better:
        score = (
            (numeric <= value).sum()
            / len(numeric)
            * 100
        )
    else:
        score = (
            (numeric >= value).sum()
            / len(numeric)
            * 100
        )

    return float(score)


benchmark_rows = comparison[
    comparison["company_id"] == selected_company_id
]

if benchmark_rows.empty:
    st.warning(
        "The selected company has no financial data."
    )
    st.stop()

benchmark_row = benchmark_rows.iloc[0]


radar_labels = []
company_scores = []
peer_scores = []

for label, column in available_metrics.items():
    metric_series = pd.to_numeric(
        comparison[column],
        errors="coerce",
    )

    company_value = pd.to_numeric(
        pd.Series([benchmark_row.get(column)]),
        errors="coerce",
    ).iloc[0]

    company_percentile = percentile_score(
        metric_series,
        company_value,
        higher_is_better=True,
    )

    valid_values = metric_series.dropna()

    if valid_values.empty:
        peer_percentile = 0.0
    else:
        peer_median = valid_values.median()

        peer_percentile = percentile_score(
            metric_series,
            peer_median,
            higher_is_better=True,
        )

    radar_labels.append(label)
    company_scores.append(company_percentile)
    peer_scores.append(peer_percentile)


radar_labels_closed = radar_labels + [
    radar_labels[0]
]

company_scores_closed = company_scores + [
    company_scores[0]
]

peer_scores_closed = peer_scores + [
    peer_scores[0]
]


st.subheader(
    f"{selected_company_name} vs {selected_group} Average"
)

radar_chart = go.Figure()

radar_chart.add_trace(
    go.Scatterpolar(
        r=company_scores_closed,
        theta=radar_labels_closed,
        fill="toself",
        name=selected_company_name,
    )
)

radar_chart.add_trace(
    go.Scatterpolar(
        r=peer_scores_closed,
        theta=radar_labels_closed,
        fill="toself",
        name="Peer Group Median",
    )
)

radar_chart.update_layout(
    polar={
        "radialaxis": {
            "visible": True,
            "range": [0, 100],
            "tickvals": [0, 20, 40, 60, 80, 100],
        }
    },
    showlegend=True,
    margin={
        "l": 40,
        "r": 40,
        "t": 40,
        "b": 40,
    },
)

st.plotly_chart(
    radar_chart,
    width="stretch",
)


st.subheader("Peer KPI Comparison")

table_columns = [
    "company_id",
    "display_name",
    "year",
    "roe_display",
    "npm_display",
    "operating_profit_margin_pct",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "asset_turnover",
    "free_cash_flow_cr",
    "debt_to_equity",
    "composite_quality_score",
]

table_columns = [
    column
    for column in table_columns
    if column in comparison.columns
]

comparison_table = comparison[
    table_columns
].copy()

comparison_table["Benchmark"] = (
    comparison_table["company_id"]
    == selected_company_id
)

comparison_table = comparison_table.rename(
    columns={
        "company_id": "Ticker",
        "display_name": "Company",
        "year": "Latest Period",
        "roe_display": "ROE %",
        "npm_display": "Net Profit Margin %",
        "operating_profit_margin_pct": "OPM %",
        "revenue_cagr_5yr": "Revenue CAGR 5yr %",
        "pat_cagr_5yr": "PAT CAGR 5yr %",
        "asset_turnover": "Asset Turnover",
        "free_cash_flow_cr": "FCF ₹ Cr",
        "debt_to_equity": "D/E",
        "composite_quality_score": "Quality Score",
    }
)

numeric_columns = comparison_table.select_dtypes(
    include="number"
).columns

comparison_table[numeric_columns] = (
    comparison_table[numeric_columns]
    .round(2)
)

comparison_table = comparison_table.sort_values(
    by=["Benchmark", "Quality Score"],
    ascending=[False, False],
    na_position="last",
)


def highlight_benchmark(row):
    """Highlight the selected benchmark company."""
    if bool(row.get("Benchmark", False)):
        return [
            "background-color: rgba(255, 215, 0, 0.20); "
            "font-weight: bold"
        ] * len(row)

    return [""] * len(row)


styled_table = comparison_table.style.apply(
    highlight_benchmark,
    axis=1,
)

st.dataframe(
    styled_table,
    width="stretch",
    hide_index=True,
)


peer_count = comparison[
    "company_id"
].nunique()

st.caption(
    f"{peer_count} companies are included in the "
    f"{selected_group} peer group. Radar values are "
    "peer-relative percentile scores from 0 to 100."
)