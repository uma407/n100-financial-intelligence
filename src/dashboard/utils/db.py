from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


# Project root:
# n100-financial-intelligence/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# SQLite database:
# n100-financial-intelligence/nifty100.db
DB_PATH = PROJECT_ROOT / "nifty100.db"


def get_connection() -> sqlite3.Connection:
    """Create and return a SQLite database connection."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database file not found at: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


def table_exists(table_name: str) -> bool:
    """Check whether a table exists in the database."""
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
    """

    with get_connection() as connection:
        result = connection.execute(
            query,
            (table_name,),
        ).fetchone()

    return result is not None


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """Return all companies."""
    query = """
        SELECT *
        FROM companies
        ORDER BY company_name
    """

    with get_connection() as connection:
        return pd.read_sql_query(query, connection)


@st.cache_data(ttl=600)
def get_ratios(
    ticker: str | int | None = None,
    year: int | str | None = None,
) -> pd.DataFrame:
    """
    Return financial-ratio data.

    The ticker argument may be:
    - company ID, such as TCS
    - company name, such as Tata Consultancy Services Ltd
    """

    query = """
        SELECT
            fr.*,
            c.company_name,
            c.bse_profile,
            s.broad_sector,
            s.sub_sector
        FROM financial_ratios fr
        LEFT JOIN companies c
            ON CAST(fr.company_id AS TEXT) = CAST(c.id AS TEXT)
        LEFT JOIN sectors s
            ON CAST(fr.company_id AS TEXT) = CAST(s.company_id AS TEXT)
        WHERE 1 = 1
    """

    params: list = []

    if ticker is not None:
        ticker_text = str(ticker).strip()

        query += """
            AND (
                LOWER(CAST(fr.company_id AS TEXT)) = LOWER(?)
                OR LOWER(c.company_name) = LOWER(?)
            )
        """

        params.extend([ticker_text, ticker_text])

    if year is not None:
        year_text = str(year).strip()

        query += """
            AND (
                CAST(fr.year AS TEXT) = ?
                OR CAST(fr.year AS TEXT) LIKE ?
            )
        """

        params.extend([year_text, f"%{year_text}"])

    query += """
        ORDER BY
            CAST(
                SUBSTR(
                    CAST(fr.year AS TEXT),
                    LENGTH(CAST(fr.year AS TEXT)) - 3,
                    4
                ) AS INTEGER
            ),
            fr.year
    """

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=params,
        )


@st.cache_data(ttl=600)
def get_pl(ticker: str | int) -> pd.DataFrame:
    """Return profit-and-loss data for one company."""

    query = """
        SELECT
            pl.*,
            c.company_name
        FROM profitandloss pl
        LEFT JOIN companies c
            ON CAST(pl.company_id AS TEXT) = CAST(c.id AS TEXT)
        WHERE 1 = 1
    """

    ticker_text = str(ticker).strip()

    query += """
        AND (
            LOWER(CAST(pl.company_id AS TEXT)) = LOWER(?)
            OR LOWER(c.company_name) = LOWER(?)
        )
    """

    query += """
        ORDER BY
            CAST(
                SUBSTR(
                    CAST(pl.year AS TEXT),
                    LENGTH(CAST(pl.year AS TEXT)) - 3,
                    4
                ) AS INTEGER
            ),
            pl.year
    """

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[ticker_text, ticker_text],
        )


@st.cache_data(ttl=600)
def get_bs(ticker: str | int) -> pd.DataFrame:
    """Return balance-sheet data for one company."""

    if not table_exists("balancesheet"):
        return pd.DataFrame()

    query = """
        SELECT
            bs.*,
            c.company_name
        FROM balancesheet bs
        LEFT JOIN companies c
            ON CAST(bs.company_id AS TEXT) = CAST(c.id AS TEXT)
        WHERE 1 = 1
    """

    ticker_text = str(ticker).strip()

    query += """
        AND (
            LOWER(CAST(bs.company_id AS TEXT)) = LOWER(?)
            OR LOWER(c.company_name) = LOWER(?)
        )
    """

    query += """
        ORDER BY
            CAST(
                SUBSTR(
                    CAST(bs.year AS TEXT),
                    LENGTH(CAST(bs.year AS TEXT)) - 3,
                    4
                ) AS INTEGER
            ),
            bs.year
    """

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[ticker_text, ticker_text],
        )


@st.cache_data(ttl=600)
def get_cf(ticker: str | int) -> pd.DataFrame:
    """Return cash-flow data for one company."""

    if not table_exists("cashflow"):
        return pd.DataFrame()

    query = """
        SELECT
            cf.*,
            c.company_name
        FROM cashflow cf
        LEFT JOIN companies c
            ON CAST(cf.company_id AS TEXT) = CAST(c.id AS TEXT)
        WHERE 1 = 1
    """

    ticker_text = str(ticker).strip()

    query += """
        AND (
            LOWER(CAST(cf.company_id AS TEXT)) = LOWER(?)
            OR LOWER(c.company_name) = LOWER(?)
        )
    """

    query += """
        ORDER BY
            CAST(
                SUBSTR(
                    CAST(cf.year AS TEXT),
                    LENGTH(CAST(cf.year AS TEXT)) - 3,
                    4
                ) AS INTEGER
            ),
            cf.year
    """

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=[ticker_text, ticker_text],
        )


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """Return company and sector information."""

    query = """
        SELECT
            s.company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector
        FROM sectors s
        LEFT JOIN companies c
            ON CAST(s.company_id AS TEXT) = CAST(c.id AS TEXT)
        ORDER BY
            s.broad_sector,
            c.company_name
    """

    with get_connection() as connection:
        return pd.read_sql_query(query, connection)


@st.cache_data(ttl=600)
def get_peers(
    group_name: str | None = None,
) -> pd.DataFrame:
    """Return peer-group data."""

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
            ON CAST(pg.company_id AS TEXT) = CAST(c.id AS TEXT)
        LEFT JOIN sectors s
            ON CAST(pg.company_id AS TEXT) = CAST(s.company_id AS TEXT)
        WHERE 1 = 1
    """

    params: list = []

    if group_name:
        query += """
            AND pg.peer_group_name = ?
        """
        params.append(group_name)

    query += """
        ORDER BY
            pg.peer_group_name,
            c.company_name
    """

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=params,
        )


@st.cache_data(ttl=600)
def get_valuation(
    ticker: str | int | None = None,
) -> pd.DataFrame:
    """
    Return valuation data.

    Before Day 26, the valuation table may not exist.
    In that case, return an empty DataFrame.
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
            ON CAST(v.company_id AS TEXT) = CAST(c.id AS TEXT)
        LEFT JOIN sectors s
            ON CAST(v.company_id AS TEXT) = CAST(s.company_id AS TEXT)
        WHERE 1 = 1
    """

    params: list = []

    if ticker is not None:
        ticker_text = str(ticker).strip()

        query += """
            AND (
                LOWER(CAST(v.company_id AS TEXT)) = LOWER(?)
                OR LOWER(c.company_name) = LOWER(?)
            )
        """

        params.extend([ticker_text, ticker_text])

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=params,
        )