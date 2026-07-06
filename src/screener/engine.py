import sqlite3
from pathlib import Path

import pandas as pd
import yaml


DB_PATH = "nifty100.db"
CONFIG_PATH = Path("config/screener_config.yaml")


def load_config(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_financial_ratios(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
    conn.close()
    return df


def add_composite_quality_score(df):
    score_columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "asset_turnover",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
    ]

    available_columns = [col for col in score_columns if col in df.columns]

    if not available_columns:
        df["composite_quality_score"] = 0
        return df

    df["composite_quality_score"] = df[available_columns].mean(axis=1, skipna=True)

    return df


def apply_threshold_filters(df, filters):
    filtered = df.copy()

    for filter_name, threshold in filters.items():
        if threshold is None:
            continue

        if filter_name == "roe_min" and "return_on_equity_pct" in filtered.columns:
            filtered = filtered[filtered["return_on_equity_pct"] >= threshold]

        elif filter_name == "debt_to_equity_max" and "debt_to_equity" in filtered.columns:
            filtered = filtered[
                (filtered["debt_to_equity"].isna())
                | (filtered["debt_to_equity"] <= threshold)
            ]

        elif filter_name == "free_cash_flow_min" and "free_cash_flow_cr" in filtered.columns:
            filtered = filtered[filtered["free_cash_flow_cr"] >= threshold]

        elif filter_name == "revenue_cagr_5yr_min" and "revenue_cagr_5yr" in filtered.columns:
            filtered = filtered[filtered["revenue_cagr_5yr"] >= threshold]

        elif filter_name == "pat_cagr_5yr_min" and "pat_cagr_5yr" in filtered.columns:
            filtered = filtered[filtered["pat_cagr_5yr"] >= threshold]

        elif filter_name == "operating_profit_margin_min" and "operating_profit_margin_pct" in filtered.columns:
            filtered = filtered[filtered["operating_profit_margin_pct"] >= threshold]

        elif filter_name == "interest_coverage_min" and "interest_coverage" in filtered.columns:
            filtered = filtered[
                (filtered["interest_coverage"].isna())
                | (filtered["interest_coverage"] >= threshold)
            ]

        elif filter_name == "net_profit_min" and "net_profit_margin_pct" in filtered.columns:
            filtered = filtered[filtered["net_profit_margin_pct"] >= threshold]

        elif filter_name == "eps_cagr_min" and "eps_cagr_5yr" in filtered.columns:
            filtered = filtered[filtered["eps_cagr_5yr"] >= threshold]

        elif filter_name == "asset_turnover_min" and "asset_turnover" in filtered.columns:
            filtered = filtered[filtered["asset_turnover"] >= threshold]

        elif filter_name == "sales_min":
            # Sales is not stored in financial_ratios in the current schema.
            # This filter is skipped safely.
            continue

        elif filter_name in [
            "pe_max",
            "pb_max",
            "dividend_yield_min",
            "market_cap_min",
        ]:
            # These fields are not available in the current financial_ratios schema.
            # Skipping safely keeps the engine robust.
            continue

    return filtered


def run_screener(custom_filters=None):
    config = load_config()
    default_filters = config.get("metrics", {})

    filters = default_filters.copy()

    if custom_filters:
        filters.update(custom_filters)

    df = load_financial_ratios()
    df = add_composite_quality_score(df)
    filtered = apply_threshold_filters(df, filters)

    if "composite_quality_score" in filtered.columns:
        filtered = filtered.sort_values(
            by="composite_quality_score",
            ascending=False
        )

    return filtered
def preset_screen(name):
    presets = {
        "quality_compounder": {
            "operating_profit_margin_min": 25,
            "free_cash_flow_min": 500,
            "revenue_cagr_5yr_min": 20,
        },
        "value_pick": {
            "operating_profit_margin_min": 25,
            "asset_turnover_min": 1,
            "free_cash_flow_min": 100,
        },
        "growth_accelerator": {
            "pat_cagr_5yr_min": 25,
            "revenue_cagr_5yr_min": 20,
            "operating_profit_margin_min": 10,
        },
        "dividend_champion": {
            "free_cash_flow_min": 4000,
            "operating_profit_margin_min": 40,
        },
        "debt_free_blue_chip": {
            "debt_to_equity_max": 0,
            "operating_profit_margin_min": 50,
            "free_cash_flow_min": 4000,
        },
        "turnaround_watch": {
            "revenue_cagr_5yr_min": 25,
            "free_cash_flow_min": 200,
            "operating_profit_margin_min": 5,
        },
    }

    if name not in presets:
        raise ValueError("Unknown preset")

    return run_screener(presets[name])

if __name__ == "__main__":
    result = run_screener(
        {
            "operating_profit_margin_min": 10,
            "revenue_cagr_5yr_min": 5,
        }
    )

    print("Filtered rows:", len(result))
    print(result.head())