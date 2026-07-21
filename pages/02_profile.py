import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.dashboard.utils.db import (
    get_bs,
    get_cf,
    get_companies,
    get_connection,
    get_pl,
    get_ratios,
    get_sectors,
)


st.header("🏢 Company Profile")
st.caption(
    "Search for a company to view its financial profile, performance trends, "
    "cash flow, and analysis."
)


def format_number(value, suffix="", decimals=2):
    """Format numeric KPI values safely."""
    if value is None or pd.isna(value):
        return "N/A"

    try:
        return f"{float(value):,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def extract_calendar_year(value):
    """Extract a four-digit year from values such as 'Mar 2024'."""
    match = re.search(r"\d{4}", str(value))
    return int(match.group()) if match else None


def latest_company_row(dataframe):
    """Return the latest available record."""
    if dataframe.empty:
        return None

    result = dataframe.copy()
    result["calendar_year"] = result["year"].apply(extract_calendar_year)

    month_order = {
        "Mar": 1,
        "Jun": 2,
        "Sep": 3,
        "Dec": 4,
    }

    result["month"] = (
        result["year"]
        .astype(str)
        .str.extract(r"^(Mar|Jun|Sep|Dec)", expand=False)
    )

    result["month_order"] = result["month"].map(month_order).fillna(0)

    result = result.sort_values(
        ["calendar_year", "month_order"],
        ascending=[False, False],
    )

    return result.iloc[0]


@st.cache_data(ttl=600)
def get_analysis(company_id):
    """Load analysis remarks for one company."""
    query = """
        SELECT company_id, year, remarks
        FROM analysis
        WHERE company_id = ?
        ORDER BY year
    """

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[str(company_id)],
        )


companies = get_companies()
sectors = get_sectors()

if companies.empty:
    st.error("Company information is not available.")
    st.stop()

companies = companies.copy()
companies["company_name"] = companies["company_name"].fillna("Unknown Company")
companies["search_label"] = (
    companies["company_name"].astype(str)
    + " — "
    + companies["id"].astype(str)
)

search_text = st.text_input(
    "Search company name or ticker",
    placeholder="Example: Reliance, Infosys, TCS...",
).strip()

if search_text:
    matching_companies = companies[
        companies["company_name"]
        .astype(str)
        .str.contains(search_text, case=False, na=False)
        |
        companies["id"]
        .astype(str)
        .str.contains(search_text, case=False, na=False)
    ].copy()
else:
    matching_companies = companies.copy()

if matching_companies.empty:
    st.warning("Ticker not found — please try another.")
    st.stop()

selected_label = st.selectbox(
    "Select Company",
    matching_companies["search_label"].tolist(),
)

selected_company = matching_companies[
    matching_companies["search_label"] == selected_label
].iloc[0]

company_id = str(selected_company["id"])
company_name = selected_company["company_name"]
bse_profile = selected_company.get("bse_profile")

sector_row = sectors[
    sectors["company_id"].astype(str) == company_id
]

if sector_row.empty:
    broad_sector = "N/A"
    sub_sector = "N/A"
else:
    broad_sector = sector_row.iloc[0].get("broad_sector", "N/A")
    sub_sector = sector_row.iloc[0].get("sub_sector", "N/A")

ratios = get_ratios(company_id)
profit_loss = get_pl(company_id)
balance_sheet = get_bs(company_id)
cash_flow = get_cf(company_id)
analysis = get_analysis(company_id)

latest_ratios = latest_company_row(ratios)

st.divider()

st.subheader(company_name)

profile_col1, profile_col2 = st.columns([3, 1])

with profile_col1:
    st.markdown(
        f"""
        **Company ID / Ticker:** `{company_id}`  
        **Sector:** {broad_sector or "N/A"}  
        **Sub-sector:** {sub_sector or "N/A"}
        """
    )

    if isinstance(bse_profile, str) and bse_profile.strip():
        if bse_profile.startswith(("http://", "https://")):
            st.markdown(f"[Open BSE company profile]({bse_profile})")
        else:
            st.write(bse_profile)
    else:
        st.info("Company description is not available in the current database.")

with profile_col2:
    if latest_ratios is not None:
        latest_year = latest_ratios.get("year", "N/A")
        st.metric("Latest Financial Period", latest_year)
    else:
        st.metric("Latest Financial Period", "N/A")

if latest_ratios is None:
    roe = None
    net_profit_margin = None
    debt_to_equity = None
    revenue_cagr = None
    free_cash_flow = None
else:
    roe = latest_ratios.get("return_on_equity_pct")

    if pd.isna(roe):
        roe = latest_ratios.get("roe")

    net_profit_margin = latest_ratios.get("net_profit_margin_pct")

    if pd.isna(net_profit_margin):
        net_profit_margin = latest_ratios.get("net_profit_margin")

    debt_to_equity = latest_ratios.get("debt_to_equity")
    revenue_cagr = latest_ratios.get("revenue_cagr_5yr")
    free_cash_flow = latest_ratios.get("free_cash_flow_cr")


# Calculate latest ROCE using available data:
# ROCE = Operating Profit / Capital Employed × 100
# Capital Employed = Total Assets - Total Liabilities
roce = None

if not profit_loss.empty and not balance_sheet.empty:
    pl_for_roce = profit_loss.copy()
    bs_for_roce = balance_sheet.copy()

    pl_for_roce["calendar_year"] = pl_for_roce["year"].apply(
        extract_calendar_year
    )
    bs_for_roce["calendar_year"] = bs_for_roce["year"].apply(
        extract_calendar_year
    )

    roce_data = pl_for_roce.merge(
        bs_for_roce[
            [
                "company_id",
                "calendar_year",
                "total_assets",
                "total_liabilities",
            ]
        ],
        on=["company_id", "calendar_year"],
        how="inner",
    )

    if not roce_data.empty:
        roce_data["capital_employed"] = (
            pd.to_numeric(roce_data["total_assets"], errors="coerce")
            - pd.to_numeric(
                roce_data["total_liabilities"],
                errors="coerce",
            )
        )

        roce_data["roce_pct"] = (
            pd.to_numeric(
                roce_data["operating_profit"],
                errors="coerce",
            )
            / roce_data["capital_employed"].replace(0, pd.NA)
            * 100
        )

        roce_data = roce_data.sort_values(
            "calendar_year",
            ascending=False,
        )

        if not roce_data.empty:
            roce = roce_data.iloc[0]["roce_pct"]


st.subheader("Key Financial Metrics")

kpi1, kpi2, kpi3 = st.columns(3)

with kpi1:
    st.metric("ROE", format_number(roe, "%"))

with kpi2:
    st.metric(
        "ROCE",
        format_number(roce, "%"),
        help=(
            "Calculated as Operating Profit divided by "
            "Total Assets minus Total Liabilities."
        ),
    )

with kpi3:
    st.metric(
        "Net Profit Margin",
        format_number(net_profit_margin, "%"),
    )

kpi4, kpi5, kpi6 = st.columns(3)

with kpi4:
    st.metric("Debt-to-Equity", format_number(debt_to_equity))

with kpi5:
    st.metric(
        "Revenue CAGR 5yr",
        format_number(revenue_cagr, "%"),
    )

with kpi6:
    st.metric(
        "Free Cash Flow",
        format_number(free_cash_flow, " Cr"),
    )


st.divider()
st.subheader("Revenue and Net Profit Trend")

if profit_loss.empty:
    st.info("Profit and loss history is not available for this company.")
else:
    pl_chart = profit_loss.copy()

    pl_chart["calendar_year"] = pl_chart["year"].apply(
        extract_calendar_year
    )

    pl_chart["sales"] = pd.to_numeric(
        pl_chart["sales"],
        errors="coerce",
    )

    pl_chart["net_profit"] = pd.to_numeric(
        pl_chart["net_profit"],
        errors="coerce",
    )

    pl_chart = (
        pl_chart.dropna(subset=["calendar_year"])
        .sort_values("calendar_year")
        .drop_duplicates("calendar_year", keep="last")
        .tail(10)
    )

    revenue_profit_chart = go.Figure()

    revenue_profit_chart.add_trace(
        go.Bar(
            x=pl_chart["calendar_year"],
            y=pl_chart["sales"],
            name="Revenue",
        )
    )

    revenue_profit_chart.add_trace(
        go.Bar(
            x=pl_chart["calendar_year"],
            y=pl_chart["net_profit"],
            name="Net Profit",
        )
    )

    revenue_profit_chart.update_layout(
        barmode="group",
        xaxis_title="Year",
        yaxis_title="Amount (₹ Crore)",
        legend_title="Metric",
        margin=dict(l=20, r=20, t=30, b=20),
    )

    st.plotly_chart(
        revenue_profit_chart,
        width="stretch",
    )


st.divider()
st.subheader("ROE and ROCE Trend")

ratio_chart = ratios.copy()

if ratio_chart.empty:
    st.info("Ratio history is not available for this company.")
else:
    ratio_chart["calendar_year"] = ratio_chart["year"].apply(
        extract_calendar_year
    )

    ratio_chart["roe_display"] = pd.to_numeric(
        ratio_chart["return_on_equity_pct"],
        errors="coerce",
    )

    if "roe" in ratio_chart.columns:
        ratio_chart["roe_display"] = ratio_chart[
            "roe_display"
        ].fillna(
            pd.to_numeric(
                ratio_chart["roe"],
                errors="coerce",
            )
        )

    ratio_chart = (
        ratio_chart.dropna(subset=["calendar_year"])
        .sort_values("calendar_year")
        .drop_duplicates("calendar_year", keep="last")
        .tail(10)
    )

    if not profit_loss.empty and not balance_sheet.empty:
        pl_trend = profit_loss.copy()
        bs_trend = balance_sheet.copy()

        pl_trend["calendar_year"] = pl_trend["year"].apply(
            extract_calendar_year
        )
        bs_trend["calendar_year"] = bs_trend["year"].apply(
            extract_calendar_year
        )

        roce_trend = pl_trend.merge(
            bs_trend[
                [
                    "company_id",
                    "calendar_year",
                    "total_assets",
                    "total_liabilities",
                ]
            ],
            on=["company_id", "calendar_year"],
            how="inner",
        )

        roce_trend["capital_employed"] = (
            pd.to_numeric(
                roce_trend["total_assets"],
                errors="coerce",
            )
            - pd.to_numeric(
                roce_trend["total_liabilities"],
                errors="coerce",
            )
        )

        roce_trend["roce_pct"] = (
            pd.to_numeric(
                roce_trend["operating_profit"],
                errors="coerce",
            )
            / roce_trend["capital_employed"].replace(0, pd.NA)
            * 100
        )

        roce_trend = (
            roce_trend.sort_values("calendar_year")
            .drop_duplicates("calendar_year", keep="last")
            .tail(10)
        )
    else:
        roce_trend = pd.DataFrame()

    roe_roce_chart = make_subplots(
        specs=[[{"secondary_y": True}]]
    )

    roe_roce_chart.add_trace(
        go.Scatter(
            x=ratio_chart["calendar_year"],
            y=ratio_chart["roe_display"],
            mode="lines+markers",
            name="ROE",
        ),
        secondary_y=False,
    )

    if not roce_trend.empty:
        roe_roce_chart.add_trace(
            go.Scatter(
                x=roce_trend["calendar_year"],
                y=roce_trend["roce_pct"],
                mode="lines+markers",
                name="ROCE",
            ),
            secondary_y=True,
        )

    roe_roce_chart.update_xaxes(title_text="Year")
    roe_roce_chart.update_yaxes(
        title_text="ROE (%)",
        secondary_y=False,
    )
    roe_roce_chart.update_yaxes(
        title_text="ROCE (%)",
        secondary_y=True,
    )

    roe_roce_chart.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        legend_title="Metric",
    )

    st.plotly_chart(
        roe_roce_chart,
        width="stretch",
    )


st.divider()
st.subheader("Pros and Cons")

if analysis.empty or analysis["remarks"].dropna().empty:
    st.info("Pros and cons are not available for this company.")
else:
    latest_analysis = analysis.copy()
    latest_analysis["calendar_year"] = latest_analysis["year"].apply(
        extract_calendar_year
    )

    latest_analysis = latest_analysis.sort_values(
        "calendar_year",
        ascending=False,
    )

    remarks_text = " ".join(
        latest_analysis["remarks"]
        .dropna()
        .astype(str)
        .tolist()
    )

    remark_items = [
        item.strip(" -•\t")
        for item in re.split(r"[\n;]+", remarks_text)
        if item.strip()
    ]

    negative_words = {
        "decline",
        "declining",
        "risk",
        "weak",
        "loss",
        "losses",
        "high debt",
        "negative",
        "concern",
        "fall",
        "volatile",
        "poor",
        "low growth",
    }

    pros = []
    cons = []

    for item in remark_items:
        item_lower = item.lower()

        if any(word in item_lower for word in negative_words):
            cons.append(item)
        else:
            pros.append(item)

    pro_column, con_column = st.columns(2)

    with pro_column:
        st.markdown("#### ✅ Pros")

        if pros:
            for item in pros:
                st.success(item)
        else:
            st.info("No positive remarks are available.")

    with con_column:
        st.markdown("#### ❌ Cons")

        if cons:
            for item in cons:
                st.error(item)
        else:
            st.info("No negative remarks are available.")


if (
    profit_loss.shape[0] < 10
    or ratios.shape[0] < 10
):
    st.caption(
        "Note: This company has fewer than 10 years of complete data. "
        "Charts show all available records."
    )