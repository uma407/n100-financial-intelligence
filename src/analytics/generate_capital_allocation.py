import sqlite3
import pandas as pd

from cashflow_kpis import capital_allocation_pattern


conn = sqlite3.connect("nifty100.db")

query = """
SELECT
    company_id,
    year,
    operating_activity,
    investing_activity,
    financing_activity
FROM cashflow
"""

df = pd.read_sql_query(query, conn)

rows = []

for _, row in df.iterrows():

    cfo_sign, cfi_sign, cff_sign, pattern = capital_allocation_pattern(
        row["operating_activity"],
        row["investing_activity"],
        row["financing_activity"]
    )

    rows.append({
        "company_id": row["company_id"],
        "year": row["year"],
        "cfo_sign": cfo_sign,
        "cfi_sign": cfi_sign,
        "cff_sign": cff_sign,
        "pattern_label": pattern
    })

result = pd.DataFrame(rows)

result.to_csv(
    "output/capital_allocation.csv",
    index=False
)

print(result.head())
print()
print("Saved to output/capital_allocation.csv")

conn.close()