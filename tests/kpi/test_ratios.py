import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
)


# 1. Net Profit Margin - Normal Case
def test_net_profit_margin():
    assert net_profit_margin(20, 100) == 20.0


# 2. Net Profit Margin - Zero Sales
def test_net_profit_margin_zero_sales():
    assert net_profit_margin(20, 0) is None


# 3. Operating Profit Margin
def test_operating_profit_margin():
    assert operating_profit_margin(25, 100) == 25.0


# 4. Operating Profit Margin - Zero Sales
def test_operating_profit_margin_zero_sales():
    assert operating_profit_margin(25, 0) is None


# 5. ROE - Normal Case
def test_return_on_equity():
    assert return_on_equity(30, 50, 50) == 30.0


# 6. ROE - Negative Equity
def test_return_on_equity_negative():
    assert return_on_equity(20, -50, 20) is None


# 7. ROCE
def test_return_on_capital_employed():
    assert return_on_capital_employed(40, 50, 50, 100) == 20.0


# 8. ROA
def test_return_on_assets():
    assert return_on_assets(50, 500) == 10.0