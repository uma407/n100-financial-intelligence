import os
import sqlite3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DB_PATH = "nifty100.db"

OUTPUT_DIR = "reports/radar_charts"

os.makedirs(OUTPUT_DIR, exist_ok=True)


METRICS = [
    "roe",
    "net_profit_margin_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "asset_turnover",
    "interest_coverage",
    "composite_quality_score",
]


def load_data():

    conn = sqlite3.connect(DB_PATH)

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn,
    )

    peers = pd.read_sql_query(
        "SELECT company_id, peer_group_name FROM peer_groups",
        conn,
    )

    conn.close()

    df = ratios.merge(
        peers,
        on="company_id",
        how="left",
    )

    df["peer_group_name"] = df["peer_group_name"].fillna(
        "No peer group assigned"
    )

    return df

def normalise_values(values):
    values = pd.to_numeric(pd.Series(values), errors="coerce").fillna(0)

    max_value = values.max()
    min_value = values.min()

    if max_value == min_value:
        return [50 for _ in values]

    return ((values - min_value) / (max_value - min_value) * 100).tolist()


def create_radar_chart(company_id, year, company_values, peer_avg_values, peer_group):
    labels = METRICS
    num_vars = len(labels)

    company_scores = normalise_values(company_values)
    peer_scores = normalise_values(peer_avg_values)

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    company_scores += company_scores[:1]
    peer_scores += peer_scores[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    ax.plot(angles, company_scores, linewidth=2, label=company_id)
    ax.fill(angles, company_scores, alpha=0.25)

    ax.plot(angles, peer_scores, linewidth=2, linestyle="--", label="Peer Average")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8)

    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_ylim(0, 100)

    ax.set_title(f"{company_id} Radar Chart ({year})\nPeer Group: {peer_group}", fontsize=12)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))

    filename = f"{company_id}_{year}_radar.png".replace(" ", "_").replace("/", "_")
    path = os.path.join(OUTPUT_DIR, filename)

    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

    return path

def generate_all_radar_charts(limit=None):
    df = load_data()

    chart_count = 0

    for _, row in df.iterrows():
        company_id = row["company_id"]
        year = row["year"]
        peer_group = row["peer_group_name"]

        company_values = [row.get(metric, 0) for metric in METRICS]

        if peer_group == "No peer group assigned":
            peer_df = df[df["year"] == year]
        else:
            peer_df = df[
                (df["peer_group_name"] == peer_group)
                & (df["year"] == year)
            ]

        peer_avg_values = [
            pd.to_numeric(peer_df[metric], errors="coerce").mean()
            if metric in peer_df.columns
            else 0
            for metric in METRICS
        ]

        create_radar_chart(
            company_id,
            year,
            company_values,
            peer_avg_values,
            peer_group,
        )

        chart_count += 1

        if limit is not None and chart_count >= limit:
            break

    print("Radar charts generated:", chart_count)
    print("Saved in:", OUTPUT_DIR)


if __name__ == "__main__":
   generate_all_radar_charts()