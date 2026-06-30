def net_profit_margin(net_profit, sales):
    """
    Net Profit Margin = (Net Profit / Sales) * 100
    """
    if sales == 0:
        return None
    return (net_profit / sales) * 100


def operating_profit_margin(operating_profit, sales):
    """
    Operating Profit Margin = (Operating Profit / Sales) * 100
    """
    if sales == 0:
        return None
    return (operating_profit / sales) * 100


def return_on_equity(net_profit, equity_capital, reserves):
    """
    ROE = Net Profit / (Equity Capital + Reserves) * 100
    """
    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return (net_profit / equity) * 100


def return_on_capital_employed(ebit, equity_capital, reserves, borrowings):
    """
    ROCE = EBIT / (Equity + Reserves + Borrowings) * 100
    """
    capital = equity_capital + reserves + borrowings

    if capital <= 0:
        return None

    return (ebit / capital) * 100


def return_on_assets(net_profit, total_assets):
    """
    ROA = Net Profit / Total Assets * 100
    """
    if total_assets == 0:
        return None

    return (net_profit / total_assets) * 100


def debt_to_equity(borrowings, equity_capital, reserves):
    """
    Debt to Equity Ratio
    """
    equity = equity_capital + reserves

    if borrowings == 0:
        return 0

    if equity <= 0:
        return None

    return borrowings / equity


def high_leverage_flag(de_ratio, sector):
    """
    High leverage if D/E > 5
    (Except Financial sector)
    """
    if de_ratio is None:
        return False

    return de_ratio > 5 and sector != "Financials"


def interest_coverage_ratio(operating_profit, other_income, interest):
    """
    Interest Coverage Ratio
    """
    if interest == 0:
        return None

    return (operating_profit + other_income) / interest


def icr_label(interest):
    """
    Label debt free companies
    """
    if interest == 0:
        return "Debt Free"

    return ""


def icr_warning(icr):
    """
    Warning if ICR < 1.5
    """
    if icr is None:
        return False

    return icr < 1.5


def net_debt(borrowings, investments):
    """
    Net Debt
    """
    return borrowings - investments


def asset_turnover(sales, total_assets):
    """
    Asset Turnover
    """
    if total_assets == 0:
        return None

    return sales / total_assets