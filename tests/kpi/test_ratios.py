import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    icr_warning,
    net_debt,
    asset_turnover,
)


# -----------------------------
# Day 08 Tests
# -----------------------------

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


# -----------------------------
# Day 09 Tests
# -----------------------------

# 9. Debt to Equity - Normal
def test_debt_to_equity_normal():
    assert debt_to_equity(100, 50, 50) == 1.0


# 10. Debt Free Company
def test_debt_to_equity_debt_free():
    assert debt_to_equity(0, 50, 50) == 0


# 11. Negative Equity
def test_debt_to_equity_negative_equity():
    assert debt_to_equity(100, -50, 20) is None


# 12. High Leverage Flag
def test_high_leverage_flag_non_financial():
    assert high_leverage_flag(6, "IT") is True


# 13. Financial Sector Exception
def test_high_leverage_flag_financials():
    assert high_leverage_flag(6, "Financials") is False


# 14. Interest Coverage Ratio
def test_interest_coverage_zero_interest():
    assert interest_coverage_ratio(100, 20, 0) is None


# 15. Debt Free Label
def test_icr_label_debt_free():
    assert icr_label(0) == "Debt Free"


# 16. Asset Turnover Zero Assets
def test_asset_turnover_zero_assets():
    assert asset_turnover(100, 0) is None