import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src" / "etl"))

from normaliser import normalize_year, normalize_ticker


# -----------------------
# normalize_year tests
# -----------------------

def test_normalize_year_mar_23():
    assert normalize_year("Mar-23") == "2023-03"

def test_normalize_year_mar_24():
    assert normalize_year("Mar-24") == "2024-03"

def test_normalize_year_fy2024():
    assert normalize_year("FY2024") == "2024-03"

def test_normalize_year_fy_2023():
    assert normalize_year("FY 2023") == "2023-03"

def test_normalize_year_2024():
    assert normalize_year("2024") == "2024-03"

def test_normalize_year_2020():
    assert normalize_year("2020") == "2020-03"

def test_normalize_year_space():
    assert normalize_year(" Mar-22 ") == "2022-03"

def test_normalize_year_apr_21():
    assert normalize_year("Apr-21") == "2021-04"

def test_normalize_year_dec_20():
    assert normalize_year("Dec-20") == "2020-12"

def test_normalize_year_jan_19():
    assert normalize_year("Jan-19") == "2019-01"

def test_normalize_year_none():
    assert normalize_year(None) is None

def test_normalize_year_blank():
    assert normalize_year("") == ""

def test_normalize_year_old():
    assert normalize_year("Mar-99") == "1999-03"

def test_normalize_year_lowercase():
    assert normalize_year("mar-23") == "2023-03"

def test_normalize_year_no_dash():
    assert normalize_year("Mar23") == "2023-03"

def test_normalize_year_unknown():
    assert normalize_year("Unknown") == "Unknown"

def test_normalize_year_jun():
    assert normalize_year("Jun-22") == "2022-06"

def test_normalize_year_sep():
    assert normalize_year("Sep-21") == "2021-09"

def test_normalize_year_oct():
    assert normalize_year("Oct-20") == "2020-10"

def test_normalize_year_nov():
    assert normalize_year("Nov-19") == "2019-11"


# -----------------------
# normalize_ticker tests
# -----------------------

def test_normalize_ticker_basic():
    assert normalize_ticker("TCS") == "TCS"

def test_normalize_ticker_lower():
    assert normalize_ticker("tcs") == "TCS"

def test_normalize_ticker_space():
    assert normalize_ticker(" TCS ") == "TCS"

def test_normalize_ticker_newline():
    assert normalize_ticker("TCS\n") == "TCS"

def test_normalize_ticker_tab():
    assert normalize_ticker("TCS\t") == "TCS"

def test_normalize_ticker_ns():
    assert normalize_ticker("TCS.NS") == "TCS"

def test_normalize_ticker_bo():
    assert normalize_ticker("TCS.BO") == "TCS"

def test_normalize_ticker_space_inside():
    assert normalize_ticker("HDFC BANK") == "HDFCBANK"

def test_normalize_ticker_none():
    assert normalize_ticker(None) is None

def test_normalize_ticker_blank():
    assert normalize_ticker("") is None

def test_normalize_ticker_number():
    assert normalize_ticker(123) == "123"

def test_normalize_ticker_mixed():
    assert normalize_ticker(" hdfcbank.ns ") == "HDFCBANK"

def test_normalize_ticker_symbol():
    assert normalize_ticker("INFY") == "INFY"

def test_normalize_ticker_long():
    assert normalize_ticker("RELIANCE") == "RELIANCE"

def test_normalize_ticker_with_many_spaces():
    assert normalize_ticker("  ICICI BANK  ") == "ICICIBANK"