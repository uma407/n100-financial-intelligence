import re
import pandas as pd


def normalize_ticker(value):
    if pd.isna(value):
        return None

    ticker = str(value).strip().upper()
    ticker = ticker.replace("\n", "")
    ticker = ticker.replace("\t", "")
    ticker = ticker.replace(" ", "")
    ticker = ticker.replace(".NS", "")
    ticker = ticker.replace(".BO", "")

    return ticker if ticker else None


def normalize_year(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    month_map = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
    }

    upper_text = text.upper()

    match = re.match(r"([A-Z]{3})[-\s]?(\d{2})$", upper_text)
    if match:
        month, year = match.groups()
        year = int(year)
        full_year = 2000 + year if year < 50 else 1900 + year
        return f"{full_year}-{month_map.get(month, '03')}"

    match = re.match(r"(\d{4})$", text)
    if match:
        return f"{text}-03"

    match = re.match(r"FY\s?(\d{4})", upper_text)
    if match:
        return f"{match.group(1)}-03"

    return text