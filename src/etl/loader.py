from pathlib import Path
import pandas as pd

from normaliser import normalize_year, normalize_ticker

RAW_DATA_PATH = Path("data/raw")

CORE_FILES = {
    "companies": "companies.xlsx",
    "profitandloss": "profitandloss.xlsx",
    "balancesheet": "balancesheet.xlsx",
    "cashflow": "cashflow.xlsx",
    "analysis": "analysis.xlsx",
    "documents": "documents.xlsx",
    "prosandcons": "prosandcons.xlsx",
}

SUPPLEMENTARY_FILES = {
    "financial_ratios": "financial_ratios.xlsx",
    "market_cap": "market_cap.xlsx",
    "peer_groups": "peer_groups.xlsx",
    "sectors": "sectors.xlsx",
    "stock_prices": "stock_prices.xlsx",
}


def clean_column_names(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def load_excel_file(file_path, header=0):
    df = pd.read_excel(file_path, header=header)
    df = clean_column_names(df)

    if "year" in df.columns:
        df["year"] = df["year"].apply(normalize_year)

    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)

    return df


def load_all_files():
    datasets = {}

    for table_name, file_name in CORE_FILES.items():
        path = RAW_DATA_PATH / file_name
        datasets[table_name] = load_excel_file(path, header=1)

    for table_name, file_name in SUPPLEMENTARY_FILES.items():
        path = RAW_DATA_PATH / file_name
        datasets[table_name] = load_excel_file(path, header=0)

    return datasets


if __name__ == "__main__":
    datasets = load_all_files()

    print("\nDATASET SUMMARY\n")

    for name, df in datasets.items():
        print(f"{name:20} Rows={len(df):6}  Cols={len(df.columns):3}")