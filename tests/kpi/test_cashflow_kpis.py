from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
)


def test_free_cash_flow():
    assert free_cash_flow(100, -40) == 60


def test_cfo_quality_high_quality():
    score, label = cfo_quality_score([120, 130, 140], [100, 100, 100])
    assert round(score, 2) == 1.30
    assert label == "High Quality"


def test_cfo_quality_moderate():
    score, label = cfo_quality_score([70, 80], [100, 100])
    assert round(score, 2) == 0.75
    assert label == "Moderate"


def test_cfo_quality_accrual_risk():
    score, label = cfo_quality_score([30, 40], [100, 100])
    assert round(score, 2) == 0.35
    assert label == "Accrual Risk"


def test_capex_intensity_asset_light():
    value, label = capex_intensity(-20, 1000)
    assert value == 2.0
    assert label == "Asset Light"


def test_capex_intensity_capital_intensive():
    value, label = capex_intensity(-100, 1000)
    assert value == 10.0
    assert label == "Capital Intensive"


def test_fcf_conversion_rate():
    assert fcf_conversion_rate(80, 100) == 80.0


def test_capital_allocation_reinvestor():
    result = capital_allocation_pattern(100, -50, -20)
    assert result == ("+", "-", "-", "Reinvestor")


def test_capital_allocation_shareholder_returns():
    result = capital_allocation_pattern(100, -50, -20, high_cfo_quality=True)
    assert result == ("+", "-", "-", "Shareholder Returns")


def test_capital_allocation_distress_signal():
    result = capital_allocation_pattern(-100, 50, 20)
    assert result == ("-", "+", "+", "Distress Signal")