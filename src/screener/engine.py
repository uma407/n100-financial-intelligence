import sqlite3
from pathlib import Path

import pandas as pd
import yaml


DB_PATH = "nifty100.db"
CONFIG_PATH = Path("config/screener_config.yaml")


def load_config(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_screener_data(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)

    ratios = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
    sectors = pd.read_sql_query("SELECT * FROM sectors", conn)

    conn.close()

    df = ratios.merge(sectors, on="company_id", how="left")
    return df


def winsorized_score(series, higher_is_better=True):
    series = pd.to_numeric(series, errors="coerce")

    if series.dropna().empty:
        return pd.Series([0] * len(series), index=series.index)

    p10 = series.quantile(0.10)
    p90 = series.quantile(0.90)

    if p10 == p90:
        return pd.Series([50] * len(series), index=series.index)

    clipped = series.clip(lower=p10, upper=p90)
    score = ((clipped - p10) / (p90 - p10)) * 100

    if not higher_is_better:
        score = 100 - score

    return score.fillna(0)


def add_composite_quality_score(df):
    df = df.copy()

    grouped_scores = []

    for _, group in df.groupby("broad_sector", dropna=False):
        group = group.copy()

        group["score_roe"] = winsorized_score(group["roe"])
        group["score_roce"] = 0
        group["score_npm"] = winsorized_score(group["net_profit_margin_pct"])

        group["score_fcf_conversion"] = winsorized_score(group["fcf_conversion_rate_pct"])
        group["score_cfo_pat"] = 0
        group["score_fcf_positive"] = (group["free_cash_flow_cr"] > 0).astype(int) * 100

        group["score_revenue_cagr"] = winsorized_score(group["revenue_cagr_5yr"])
        group["score_pat_cagr"] = winsorized_score(group["pat_cagr_5yr"])

        group["score_de"] = winsorized_score(group["debt_to_equity"], higher_is_better=False)
        group["score_icr"] = winsorized_score(group["interest_coverage"])

        group["composite_quality_score"] = (
            group["score_roe"] * 0.15
            + group["score_roce"] * 0.10
            + group["score_npm"] * 0.10
            + group["score_fcf_conversion"] * 0.15
            + group["score_cfo_pat"] * 0.10
            + group["score_fcf_positive"] * 0.05
            + group["score_revenue_cagr"] * 0.10
            + group["score_pat_cagr"] * 0.10
            + group["score_de"] * 0.10
            + group["score_icr"] * 0.05
        )

        grouped_scores.append(group)

    return pd.concat(grouped_scores, ignore_index=True)


def apply_threshold_filters(df, filters):
    filtered = df.copy()

    for filter_name, threshold in filters.items():
        if threshold is None:
            continue

        if filter_name == "roe_min" and "roe" in filtered.columns:
            filtered = filtered[filtered["roe"] >= threshold]

        elif filter_name == "debt_to_equity_max" and "debt_to_equity" in filtered.columns:
            filtered = filtered[
                (filtered["broad_sector"] == "Financials")
                | (filtered["debt_to_equity"].isna())
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

        elif filter_name == "eps_cagr_min" and "eps_cagr_5yr" in filtered.columns:
            filtered = filtered[filtered["eps_cagr_5yr"] >= threshold]

        elif filter_name == "asset_turnover_min" and "asset_turnover" in filtered.columns:
            filtered = filtered[filtered["asset_turnover"] >= threshold]

    return filtered


def run_screener(custom_filters=None):
    config = load_config()
    default_filters = config.get("metrics", {})

    filters = default_filters.copy()

    if custom_filters:
        filters.update(custom_filters)

    df = load_screener_data()
    df = add_composite_quality_score(df)
    filtered = apply_threshold_filters(df, filters)

    return filtered.sort_values("composite_quality_score", ascending=False)


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
    print(result[["company_id", "year", "broad_sector", "composite_quality_score"]].head())