import re

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_connection


st.header("📄 Annual Reports")
st.caption(
    "View the latest financial summary and historical performance "
    "for every company."
)


def extract_calendar_year(value):
    """Extract the calendar year from strings like Mar-2025."""
    match = re.search(r"\d{4}", str(value))
    if match:
        return int(match.group())
    return None


def keep_latest(df: pd.DataFrame) -> pd.DataFrame:
    """Keep latest annual record for every company."""
    if df.empty:
        return df

    temp = df.copy()

    temp["calendar_year"] = temp["year"].apply(extract_calendar_year)

    temp["month"] = (
        temp["year"]
        .astype(str)
        .str.extract(r"^(Mar|Jun|Sep|Dec)", expand=False)
    )

    priority = {
        "Mar": 4,
        "Jun": 3,
        "Sep": 2,
        "Dec": 1,
    }

    temp["priority"] = temp["month"].map(priority).fillna(0)

    return (
        temp.dropna(subset=["calendar_year"])
        .sort_values(
            [
                "company_id",
                "calendar_year",
                "priority",
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
    )


@st.cache_data
def load_data():

    conn = get_connection()

    try:

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            conn,
        )

        profit = pd.read_sql_query(
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
            conn,
        )

        balance = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                total_assets,
                total_liabilities
            FROM balancesheet
            """,
            conn,
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
            conn,
        )

        documents = pd.read_sql_query(
            """
            SELECT *
            FROM documents
            """,
            conn,
        )

    finally:
        conn.close()

    latest_profit = keep_latest(profit)
    latest_balance = keep_latest(balance)
    latest_cashflow = keep_latest(cashflow)

    for df in [
        companies,
        latest_profit,
        latest_balance,
        latest_cashflow,
    ]:
        df["company_id"] = df["company_id"].astype(str)

    latest = (
        companies
        .merge(
            latest_profit,
            on="company_id",
            how="left",
        )
        .merge(
            latest_balance,
            on="company_id",
            how="left",
            suffixes=("", "_bs"),
        )
        .merge(
            latest_cashflow,
            on="company_id",
            how="left",
            suffixes=("", "_cf"),
        )
    )

    numeric_columns = [
        "sales",
        "operating_profit",
        "net_profit",
        "eps",
        "total_assets",
        "total_liabilities",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    for col in numeric_columns:
        if col in latest.columns:
            latest[col] = pd.to_numeric(
                latest[col],
                errors="coerce",
            )

    return (
        latest,
        profit,
        documents,
    )


latest_data, profit_history, documents = load_data()


company = st.selectbox(
    "Select Company",
    sorted(
        latest_data["company_name"].dropna().unique()
    ),
)

current = latest_data[
    latest_data["company_name"] == company
].iloc[0]

company_id = current["company_id"]

history = profit_history[
    profit_history["company_id"].astype(str) == company_id
].copy()

history["calendar_year"] = (
    history["year"].apply(extract_calendar_year)
)

history = (
    history.sort_values("calendar_year")
    .drop_duplicates(
        subset="calendar_year",
        keep="last",
    )
)


st.subheader("Latest Financial Summary")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Revenue",
    (
        f"₹{current['sales']:,.2f} Cr"
        if pd.notna(current["sales"])
        else "N/A"
    ),
)

c2.metric(
    "Operating Profit",
    (
        f"₹{current['operating_profit']:,.2f} Cr"
        if pd.notna(current["operating_profit"])
        else "N/A"
    ),
)

c3.metric(
    "Net Profit",
    (
        f"₹{current['net_profit']:,.2f} Cr"
        if pd.notna(current["net_profit"])
        else "N/A"
    ),
)

c4.metric(
    "EPS",
    (
        f"{current['eps']:.2f}"
        if pd.notna(current["eps"])
        else "N/A"
    ),
)
st.divider()

st.subheader("Financial Performance Trends")

metric = st.selectbox(
    "Select Metric",
    [
        "Revenue",
        "Operating Profit",
        "Net Profit",
        "EPS",
    ],
)

metric_map = {
    "Revenue": "sales",
    "Operating Profit": "operating_profit",
    "Net Profit": "net_profit",
    "EPS": "eps",
}

selected_column = metric_map[metric]

chart_data = history.dropna(
    subset=[
        "calendar_year",
        selected_column,
    ]
).copy()

if chart_data.empty:
    st.info(
        "No historical data available for this metric."
    )
else:

    line_chart = px.line(
        chart_data,
        x="calendar_year",
        y=selected_column,
        markers=True,
        text=selected_column,
        labels={
            "calendar_year": "Year",
            selected_column: metric,
        },
    )

    line_chart.update_traces(
        textposition="top center",
    )

    line_chart.update_layout(
        margin={
            "l": 20,
            "r": 20,
            "t": 30,
            "b": 20,
        },
        xaxis_title="Financial Year",
        yaxis_title=metric,
    )

    st.plotly_chart(
        line_chart,
        width="stretch",
    )


st.divider()

st.subheader("Historical Financial Table")

display_history = history[
    [
        "calendar_year",
        "sales",
        "operating_profit",
        "net_profit",
        "eps",
    ]
].rename(
    columns={
        "calendar_year": "Year",
        "sales": "Revenue ₹ Cr",
        "operating_profit": "Operating Profit ₹ Cr",
        "net_profit": "Net Profit ₹ Cr",
        "eps": "EPS",
    }
)

numeric_columns = display_history.select_dtypes(
    include="number"
).columns

display_history[numeric_columns] = (
    display_history[numeric_columns]
    .round(2)
)

st.dataframe(
    display_history,
    width="stretch",
    hide_index=True,
)


st.divider()

st.subheader("Available Company Documents")

if documents.empty:

    st.info(
        "No documents are available in the database."
    )

else:

    possible_company_columns = [
        "company_id",
        "companyid",
        "company",
    ]

    company_column = None

    for column in possible_company_columns:

        if column in documents.columns:
            company_column = column
            break

    if company_column:

        docs = documents[
            documents[company_column]
            .astype(str)
            == company_id
        ].copy()

    else:

        docs = documents.copy()

    if docs.empty:

        st.info(
            "No annual reports found for this company."
        )

    else:

        st.dataframe(
            docs,
            width="stretch",
            hide_index=True,
        )
        st.divider()

st.subheader("Download Financial Data")


download_history = display_history.copy()

history_csv = download_history.to_csv(
    index=False
).encode("utf-8")


download_col1, download_col2 = st.columns(2)


download_col1.download_button(
    label="Download Financial History",
    data=history_csv,
    file_name=(
        f"{company.replace(' ', '_').lower()}"
        "_financial_history.csv"
    ),
    mime="text/csv",
)


if not documents.empty and "docs" in locals() and not docs.empty:

    documents_csv = docs.to_csv(
        index=False
    ).encode("utf-8")

    download_col2.download_button(
        label="Download Document List",
        data=documents_csv,
        file_name=(
            f"{company.replace(' ', '_').lower()}"
            "_documents.csv"
        ),
        mime="text/csv",
    )

else:

    download_col2.button(
        "Download Document List",
        disabled=True,
    )


st.divider()

st.subheader("Company Financial Snapshot")


snapshot_data = {
    "Company": company,
    "Latest Revenue ₹ Cr": (
        round(current["sales"], 2)
        if pd.notna(current["sales"])
        else None
    ),
    "Latest Operating Profit ₹ Cr": (
        round(current["operating_profit"], 2)
        if pd.notna(current["operating_profit"])
        else None
    ),
    "Latest Net Profit ₹ Cr": (
        round(current["net_profit"], 2)
        if pd.notna(current["net_profit"])
        else None
    ),
    "Latest EPS": (
        round(current["eps"], 2)
        if pd.notna(current["eps"])
        else None
    ),
    "Total Assets ₹ Cr": (
        round(current["total_assets"], 2)
        if pd.notna(current["total_assets"])
        else None
    ),
    "Total Liabilities ₹ Cr": (
        round(current["total_liabilities"], 2)
        if pd.notna(current["total_liabilities"])
        else None
    ),
    "Operating Cash Flow ₹ Cr": (
        round(current["operating_activity"], 2)
        if pd.notna(current["operating_activity"])
        else None
    ),
    "Net Cash Flow ₹ Cr": (
        round(current["net_cash_flow"], 2)
        if pd.notna(current["net_cash_flow"])
        else None
    ),
}


snapshot_table = pd.DataFrame(
    [
        {
            "Metric": metric_name,
            "Value": metric_value,
        }
        for metric_name, metric_value
        in snapshot_data.items()
    ]
)


st.dataframe(
    snapshot_table,
    width="stretch",
    hide_index=True,
)


snapshot_csv = snapshot_table.to_csv(
    index=False
).encode("utf-8")


st.download_button(
    label="Download Company Snapshot",
    data=snapshot_csv,
    file_name=(
        f"{company.replace(' ', '_').lower()}"
        "_financial_snapshot.csv"
    ),
    mime="text/csv",
)


st.divider()

st.success(
    "Annual report analysis loaded successfully."
)

st.caption(
    "Financial values are displayed from the latest available "
    "annual records in the SQLite database. Document availability "
    "depends on the records stored in the documents table."
)