from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


# Project root:
# n100-financial-intelligence/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Database location:
# n100-financial-intelligence/nifty100.db
DB_PATH = PROJECT_ROOT / "nifty100.db"


def get_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite database connection.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database file not found at: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


def table_exists(table_name: str) -> bool:
    """
    Check whether a table exists in the SQLite database.
    """
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
    """

    with get_connection() as conn:
        result = conn.execute(query, (table_name,)).fetchone()

    return result is not None


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """
    Return all companies.
    """
    query = """
        SELECT *
        FROM companies
        ORDER BY company_name
    """

    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


@st.cache_data(ttl=600)
def get_ratios(
    ticker: str | int | None = None,
    year: int | None = None,
) -> pd.DataFrame:
    """
    Return financial ratios.

    ticker may be:
    - company_id
    - company name
    - ticker column, if available in companies table
    """

    query = """
        SELECT
            fr.*,
            c.company_name,
            s.broad_sector,
            s.sub_sector
        FROM financial_ratios fr
        LEFT JOIN companies c
            ON fr.company_id = c.id
        LEFT JOIN sectors s
            ON fr.company_id = s.company_id
        WHERE 1 = 1
    """

    params: list = []

    if ticker is not None:
        ticker_text = str(ticker).strip()

        if ticker_text.isdigit():
            query += " AND fr.company_id = ?"
            params.append(int(ticker_text))
        else:
            query += " AND LOWER(c.company_name) = LOWER(?)"
            params.append(ticker_text)

    if year is not None:
        query += " AND fr.year = ?"
        params.append(year)

    query += " ORDER BY fr.year"

    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_pl(ticker: str | int) -> pd.DataFrame:
    """
    Return profit-and-loss data for one company.
    """
    query = """
        SELECT
            pl.*,
            c.company_name
        FROM profitandloss pl
        LEFT JOIN companies c
            ON pl.company_id = c.id
        WHERE 1 = 1
    """

    params: list = []
    ticker_text = str(ticker).strip()

    if ticker_text.isdigit():
        query += " AND pl.company_id = ?"
        params.append(int(ticker_text))
    else:
        query += " AND LOWER(c.company_name) = LOWER(?)"
        params.append(ticker_text)

    query += " ORDER BY pl.year"

    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_bs(ticker: str | int) -> pd.DataFrame:
    """
    Return balance-sheet data for one company.
    """
    if not table_exists("balancesheet"):
        return pd.DataFrame()

    query = """
        SELECT
            bs.*,
            c.company_name
        FROM balancesheet bs
        LEFT JOIN companies c
            ON bs.company_id = c.id
        WHERE 1 = 1
    """

    params: list = []
    ticker_text = str(ticker).strip()

    if ticker_text.isdigit():
        query += " AND bs.company_id = ?"
        params.append(int(ticker_text))
    else:
        query += " AND LOWER(c.company_name) = LOWER(?)"
        params.append(ticker_text)

    query += " ORDER BY bs.year"

    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_cf(ticker: str | int) -> pd.DataFrame:
    """
    Return cash-flow data for one company.
    """
    if not table_exists("cashflow"):
        return pd.DataFrame()

    query = """
        SELECT
            cf.*,
            c.company_name
        FROM cashflow cf
        LEFT JOIN companies c
            ON cf.company_id = c.id
        WHERE 1 = 1
    """

    params: list = []
    ticker_text = str(ticker).strip()

    if ticker_text.isdigit():
        query += " AND cf.company_id = ?"
        params.append(int(ticker_text))
    else:
        query += " AND LOWER(c.company_name) = LOWER(?)"
        params.append(ticker_text)

    query += " ORDER BY cf.year"

    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """
    Return company and sector information.
    """
    query = """
        SELECT
            s.company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector
        FROM sectors s
        LEFT JOIN companies c
            ON s.company_id = c.id
        ORDER BY
            s.broad_sector,
            c.company_name
    """

    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


@st.cache_data(ttl=600)
def get_peers(group_name: str | None = None) -> pd.DataFrame:
    """
    Return peer-group data.
    """
    query = """
        SELECT
            pg.id,
            pg.company_id,
            pg.peer_group_name,
            c.company_name,
            s.broad_sector,
            s.sub_sector
        FROM peer_groups pg
        LEFT JOIN companies c
            ON pg.company_id = c.id
        LEFT JOIN sectors s
            ON pg.company_id = s.company_id
        WHERE 1 = 1
    """

    params: list = []

    if group_name:
        query += " AND pg.peer_group_name = ?"
        params.append(group_name)

    query += " ORDER BY pg.peer_group_name, c.company_name"

    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_valuation(ticker: str | int | None = None) -> pd.DataFrame:
    """
    Return valuation data.

    Before Day 26, the valuation table may not exist.
    In that case, return an empty DataFrame instead of crashing.
    """
    if not table_exists("valuation"):
        return pd.DataFrame()

    query = """
        SELECT
            v.*,
            c.company_name,
            s.broad_sector,
            s.sub_sector
        FROM valuation v
        LEFT JOIN companies c
            ON v.company_id = c.id
        LEFT JOIN sectors s
            ON v.company_id = s.company_id
        WHERE 1 = 1
    """

    params: list = []

    if ticker is not None:
        ticker_text = str(ticker).strip()

        if ticker_text.isdigit():
            query += " AND v.company_id = ?"
            params.append(int(ticker_text))
        else:
            query += " AND LOWER(c.company_name) = LOWER(?)"
            params.append(ticker_text)

    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)