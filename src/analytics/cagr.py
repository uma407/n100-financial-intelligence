def calculate_cagr(start_value, end_value, years):
    """
    CAGR = ((end / start) ** (1 / years) - 1) * 100
    Returns: (value, flag)
    """

    if years <= 0:
        return None, "INSUFFICIENT"

    if start_value == 0:
        return None, "ZERO_BASE"

    if start_value > 0 and end_value > 0:
        cagr = ((end_value / start_value) ** (1 / years) - 1) * 100
        return cagr, "OK"

    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"

    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"

    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"

    return None, "ZERO_BASE"


def get_cagr_from_series(values, years):
    """
    Calculates CAGR from a list of yearly values.
    Example: years=5 needs at least 6 values.
    """

    if len(values) < years + 1:
        return None, "INSUFFICIENT"

    start_value = values[-(years + 1)]
    end_value = values[-1]

    return calculate_cagr(start_value, end_value, years)


def revenue_cagr(values, years):
    return get_cagr_from_series(values, years)


def pat_cagr(values, years):
    return get_cagr_from_series(values, years)


def eps_cagr(values, years):
    return get_cagr_from_series(values, years)