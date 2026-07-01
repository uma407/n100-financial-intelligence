import pytest

from src.analytics.cagr import (
    calculate_cagr,
    get_cagr_from_series,
    revenue_cagr,
    pat_cagr,
    eps_cagr,
)


def test_calculate_cagr_normal_case():
    value, flag = calculate_cagr(100, 200, 5)
    assert round(value, 2) == 14.87
    assert flag == "OK"


def test_calculate_cagr_zero_base():
    value, flag = calculate_cagr(0, 200, 5)
    assert value is None
    assert flag == "ZERO_BASE"


def test_calculate_cagr_decline_to_loss():
    value, flag = calculate_cagr(100, -50, 5)
    assert value is None
    assert flag == "DECLINE_TO_LOSS"


def test_calculate_cagr_turnaround():
    value, flag = calculate_cagr(-100, 50, 5)
    assert value is None
    assert flag == "TURNAROUND"


def test_calculate_cagr_both_negative():
    value, flag = calculate_cagr(-100, -50, 5)
    assert value is None
    assert flag == "BOTH_NEGATIVE"


def test_calculate_cagr_insufficient_years():
    value, flag = calculate_cagr(100, 200, 0)
    assert value is None
    assert flag == "INSUFFICIENT"


def test_get_cagr_from_series_insufficient_data():
    value, flag = get_cagr_from_series([100, 120, 140], 5)
    assert value is None
    assert flag == "INSUFFICIENT"


def test_revenue_cagr_3yr():
    value, flag = revenue_cagr([100, 120, 140, 160], 3)
    assert round(value, 2) == 16.96
    assert flag == "OK"


def test_pat_cagr_5yr():
    value, flag = pat_cagr([100, 110, 120, 130, 140, 150], 5)
    assert round(value, 2) == 8.45
    assert flag == "OK"


def test_eps_cagr_10yr():
    value, flag = eps_cagr([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 10)
    assert round(value, 2) == 7.18
    assert flag == "OK"