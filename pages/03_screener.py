import pandas as pd
import streamlit as st

from src.dashboard.utils.db import get_ratios


st.header("🔍 Nifty 100 Stock Screener")
st.caption(
    "Filter companies using profitability, growth, cash-flow, "
    "leverage, and operating-efficiency metrics."
)


@st.cache_data(ttl=600)
def load_screener_data() -> pd.DataFrame:
    """Load the latest available annual record for every company."""
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
        .str.extract(r"^(Mar|Jun|Sep|Dec)", expand=False)
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
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "operating_profit_margin_pct",
        "interest_coverage",
        "asset_turnover",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

    if "return_on_equity_pct" in data.columns:
        data["roe_display"] = data[
            "return_on_equity_pct"
        ]

        if "roe" in data.columns:
            data["roe_display"] = data[
                "roe_display"
            ].fillna(data["roe"])
    else:
        data["roe_display"] = data.get(
            "roe",
            pd.Series(index=data.index, dtype=float),
        )

    return data


data = load_screener_data()

if data.empty:
    st.warning("No screener data is available.")
    st.stop()


def safe_min(
    column: str,
    default: float = 0.0,
) -> float:
    """Return a safe numeric minimum for a column."""
    if column not in data.columns:
        return default

    values = pd.to_numeric(
        data[column],
        errors="coerce",
    ).dropna()

    if values.empty:
        return default

    return float(values.min())


def safe_max(
    column: str,
    default: float = 100.0,
) -> float:
    """Return a safe numeric maximum for a column."""
    if column not in data.columns:
        return default

    values = pd.to_numeric(
        data[column],
        errors="coerce",
    ).dropna()

    if values.empty:
        return default

    return float(values.max())


PRESETS = {
    "Quality": {
        "roe_min": 15.0,
        "de_max": 1.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 8.0,
        "pat_cagr_min": 8.0,
        "opm_min": 12.0,
        "asset_turnover_min": 0.5,
    },
    "Value": {
        "roe_min": 10.0,
        "de_max": 1.5,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 8.0,
        "asset_turnover_min": 0.3,
    },
    "Growth": {
        "roe_min": 12.0,
        "de_max": 2.0,
        "fcf_min": -500.0,
        "revenue_cagr_min": 15.0,
        "pat_cagr_min": 15.0,
        "opm_min": 10.0,
        "asset_turnover_min": 0.3,
    },
    "Dividend": {
        "roe_min": 10.0,
        "de_max": 1.5,
        "fcf_min": 100.0,
        "revenue_cagr_min": 3.0,
        "pat_cagr_min": 3.0,
        "opm_min": 8.0,
        "asset_turnover_min": 0.3,
    },
    "Debt-Free": {
        "roe_min": 8.0,
        "de_max": 0.10,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 5.0,
        "asset_turnover_min": 0.2,
    },
    "Turnaround": {
        "roe_min": 0.0,
        "de_max": 3.0,
        "fcf_min": -1000.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "asset_turnover_min": 0.1,
    },
}


DEFAULT_FILTERS = {
    "roe_min": safe_min("roe_display", -50.0),
    "de_max": safe_max("debt_to_equity", 10.0),
    "fcf_min": safe_min("free_cash_flow_cr", -5000.0),
    "revenue_cagr_min": safe_min(
        "revenue_cagr_5yr",
        -50.0,
    ),
    "pat_cagr_min": safe_min(
        "pat_cagr_5yr",
        -100.0,
    ),
    "opm_min": safe_min(
        "operating_profit_margin_pct",
        -50.0,
    ),
    "asset_turnover_min": safe_min(
        "asset_turnover",
        0.0,
    ),
}


for key, value in DEFAULT_FILTERS.items():
    if key not in st.session_state:
        st.session_state[key] = float(value)


def apply_preset(preset_name: str) -> None:
    """Apply a preset to the active screener controls."""
    preset = PRESETS[preset_name]

    for key, value in preset.items():
        st.session_state[key] = float(value)


st.subheader("Preset Screens")

preset_names = [
    "Quality",
    "Value",
    "Growth",
    "Dividend",
    "Debt-Free",
    "Turnaround",
]

preset_columns = st.columns(6)

for column, preset_name in zip(
    preset_columns,
    preset_names,
):
    with column:
        st.button(
            preset_name,
            key=f"preset_{preset_name}",
            on_click=apply_preset,
            args=(preset_name,),
            width="stretch",
        )


st.sidebar.subheader("Screener Filters")

roe_min = st.sidebar.slider(
    "ROE minimum (%)",
    min_value=-50.0,
    max_value=100.0,
    step=1.0,
    key="roe_min",
)

de_max = st.sidebar.slider(
    "Debt-to-Equity maximum",
    min_value=0.0,
    max_value=max(
        10.0,
        round(
            safe_max(
                "debt_to_equity",
                10.0,
            ) + 1.0,
            1,
        ),
    ),
    step=0.1,
    key="de_max",
)

fcf_minimum = min(
    -5000.0,
    float(
        round(
            safe_min(
                "free_cash_flow_cr",
                -5000.0,
            )
        )
    ),
)

fcf_maximum = max(
    5000.0,
    float(
        round(
            safe_max(
                "free_cash_flow_cr",
                5000.0,
            )
        )
    ),
)

fcf_min = st.sidebar.slider(
    "Free Cash Flow minimum (₹ Cr)",
    min_value=fcf_minimum,
    max_value=fcf_maximum,
    step=100.0,
    key="fcf_min",
)

revenue_cagr_min = st.sidebar.slider(
    "Revenue CAGR 5yr minimum (%)",
    min_value=-50.0,
    max_value=100.0,
    step=1.0,
    key="revenue_cagr_min",
)

pat_cagr_min = st.sidebar.slider(
    "PAT CAGR 5yr minimum (%)",
    min_value=-100.0,
    max_value=150.0,
    step=1.0,
    key="pat_cagr_min",
)

opm_min = st.sidebar.slider(
    "Operating Profit Margin minimum (%)",
    min_value=-50.0,
    max_value=100.0,
    step=1.0,
    key="opm_min",
)

asset_turnover_min = st.sidebar.slider(
    "Asset Turnover minimum",
    min_value=0.0,
    max_value=max(
        5.0,
        round(
            safe_max(
                "asset_turnover",
                5.0,
            ) + 0.5,
            1,
        ),
    ),
    step=0.1,
    key="asset_turnover_min",
)


icr_available = (
    "interest_coverage" in data.columns
    and data["interest_coverage"].notna().any()
)

if icr_available:
    icr_min = st.sidebar.slider(
        "Interest Coverage minimum",
        min_value=-50.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
    )
else:
    icr_min = None

    st.sidebar.slider(
        "Interest Coverage minimum",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        disabled=True,
        help=(
            "Interest Coverage values are unavailable "
            "in the database."
        ),
    )


st.sidebar.markdown("---")
st.sidebar.caption(
    "Unavailable in the current database"
)

st.sidebar.slider(
    "P/E maximum",
    min_value=0.0,
    max_value=100.0,
    value=100.0,
    disabled=True,
    help="P/E data is not currently available.",
)

st.sidebar.slider(
    "P/B maximum",
    min_value=0.0,
    max_value=20.0,
    value=20.0,
    disabled=True,
    help="P/B data is not currently available.",
)

st.sidebar.slider(
    "Dividend Yield minimum (%)",
    min_value=0.0,
    max_value=15.0,
    value=0.0,
    disabled=True,
    help=(
        "Dividend Yield data is not currently available."
    ),
)


filtered = data.copy()

filter_rules = [
    ("roe_display", ">=", roe_min),
    ("debt_to_equity", "<=", de_max),
    ("free_cash_flow_cr", ">=", fcf_min),
    (
        "revenue_cagr_5yr",
        ">=",
        revenue_cagr_min,
    ),
    (
        "pat_cagr_5yr",
        ">=",
        pat_cagr_min,
    ),
    (
        "operating_profit_margin_pct",
        ">=",
        opm_min,
    ),
    (
        "asset_turnover",
        ">=",
        asset_turnover_min,
    ),
]

if icr_available and icr_min is not None:
    filter_rules.append(
        (
            "interest_coverage",
            ">=",
            icr_min,
        )
    )


for column, operator, threshold in filter_rules:
    if column not in filtered.columns:
        continue

    numeric_series = pd.to_numeric(
        filtered[column],
        errors="coerce",
    )

    if operator == ">=":
        filtered = filtered[
            numeric_series >= threshold
        ]

    elif operator == "<=":
        filtered = filtered[
            numeric_series <= threshold
        ]


if "composite_quality_score" in filtered.columns:
    filtered = filtered.sort_values(
        "composite_quality_score",
        ascending=False,
        na_position="last",
    )


result_count = len(filtered)

if result_count == 1:
    st.success(
        "1 company matches your filters."
    )
else:
    st.success(
        f"{result_count} companies match your filters."
    )


visible_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "year",
    "composite_quality_score",
    "roe_display",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "interest_coverage",
    "asset_turnover",
]

visible_columns = [
    column
    for column in visible_columns
    if column in filtered.columns
]

results = filtered[
    visible_columns
].copy()

results = results.rename(
    columns={
        "company_id": "Ticker",
        "company_name": "Company",
        "broad_sector": "Sector",
        "year": "Latest Period",
        "composite_quality_score": "Quality Score",
        "roe_display": "ROE %",
        "debt_to_equity": "D/E",
        "free_cash_flow_cr": "FCF ₹ Cr",
        "revenue_cagr_5yr": "Revenue CAGR 5yr %",
        "pat_cagr_5yr": "PAT CAGR 5yr %",
        "operating_profit_margin_pct": "OPM %",
        "interest_coverage": "ICR",
        "asset_turnover": "Asset Turnover",
    }
)

numeric_result_columns = results.select_dtypes(
    include="number"
).columns

results[numeric_result_columns] = results[
    numeric_result_columns
].round(2)


st.dataframe(
    results,
    width="stretch",
    hide_index=True,
)


csv_data = results.to_csv(
    index=False,
).encode("utf-8")

st.download_button(
    label="⬇️ Download Screener Results as CSV",
    data=csv_data,
    file_name="nifty100_screener_results.csv",
    mime="text/csv",
    disabled=results.empty,
)


if results.empty:
    st.info(
        "No companies match the selected values. "
        "Reduce one or more filter thresholds."
    )


unavailable_metrics = [
    "P/E",
    "P/B",
    "Dividend Yield",
]

if not icr_available:
    unavailable_metrics.append(
        "Interest Coverage"
    )

st.caption(
    "Unavailable metrics: "
    + ", ".join(unavailable_metrics)
    + ". These filters are disabled and are not used "
    "to remove companies."
)