import sqlite3
import pandas as pd

DB_PATH = "nifty100.db"


def load_data():
    conn = sqlite3.connect(DB_PATH)

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn
    )

    peers = pd.read_sql_query(
        "SELECT * FROM peer_groups",
        conn
    )

    conn.close()

    df = ratios.merge(peers, on="company_id", how="left")

    df["peer_group_name"] = df["peer_group_name"].fillna(
        "No peer group assigned"
    )

    return df


def create_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS peer_percentiles(

        company_id TEXT,

        peer_group_name TEXT,

        metric TEXT,

        value REAL,

        percentile_rank REAL,

        year TEXT

    )
    """)

    cur.execute("DELETE FROM peer_percentiles")

    conn.commit()
    conn.close()


def percent_rank(series, reverse=False):

    s = series.rank(method="min", pct=True)

    if reverse:
        s = 1 - s

    return s * 100


METRICS = {

    "roe": False,

    "net_profit_margin_pct": False,

    "debt_to_equity": True,

    "revenue_cagr_5yr": False,

    "pat_cagr_5yr": False,

    "eps_cagr_5yr": False,

    "interest_coverage": False,

    "asset_turnover": False,

    "composite_quality_score": False,

}


def populate_peer_percentiles():
    create_table()

    df = load_data()

    rows = []

    for (peer_group, year), group in df.groupby(["peer_group_name", "year"]):
        group = group.copy()

        if peer_group == "No peer group assigned":
            for _, row in group.iterrows():
                rows.append(
                    (
                        row["company_id"],
                        peer_group,
                        "No peer group assigned",
                        None,
                        None,
                        row["year"],
                    )
                )
            continue

        for metric, reverse in METRICS.items():
            if metric not in group.columns:
                continue

            valid_group = group[["company_id", "peer_group_name", "year", metric]].copy()
            valid_group[metric] = pd.to_numeric(valid_group[metric], errors="coerce")
            valid_group = valid_group.dropna(subset=[metric])

            if valid_group.empty:
                continue

            valid_group["percentile_rank"] = percent_rank(
                valid_group[metric],
                reverse=reverse,
            )

            for _, row in valid_group.iterrows():
                rows.append(
                    (
                        row["company_id"],
                        row["peer_group_name"],
                        metric,
                        row[metric],
                        row["percentile_rank"],
                        row["year"],
                    )
                )

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executemany(
        """
        INSERT INTO peer_percentiles
        (
            company_id,
            peer_group_name,
            metric,
            value,
            percentile_rank,
            year
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    conn.commit()

    count = cur.execute(
        "SELECT COUNT(*) FROM peer_percentiles"
    ).fetchone()[0]

    groups = cur.execute(
        "SELECT COUNT(DISTINCT peer_group_name) FROM peer_percentiles"
    ).fetchone()[0]

    conn.close()

    print("peer_percentiles populated")
    print("Rows inserted:", count)
    print("Peer groups:", groups)


if __name__ == "__main__":
    populate_peer_percentiles()