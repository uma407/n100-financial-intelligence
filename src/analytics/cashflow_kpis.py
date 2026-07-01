def free_cash_flow(operating_activity, investing_activity):
    """
    Free Cash Flow = Operating Activity + Investing Activity
    Negative value is allowed.
    """
    return operating_activity + investing_activity


def cfo_quality_score(cfo_values, pat_values):
    """
    CFO Quality = average CFO / PAT over available years.
    > 1.0 = High Quality
    0.5 to 1.0 = Moderate
    < 0.5 = Accrual Risk
    """
    ratios = []

    for cfo, pat in zip(cfo_values, pat_values):
        if pat == 0:
            continue
        ratios.append(cfo / pat)

    if not ratios:
        return None, None

    avg_score = sum(ratios) / len(ratios)

    if avg_score > 1.0:
        label = "High Quality"
    elif avg_score >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return avg_score, label


def capex_intensity(investing_activity, sales):
    """
    CapEx Intensity = abs(investing_activity) / sales * 100
    """
    if sales == 0:
        return None, None

    value = abs(investing_activity) / sales * 100

    if value < 3:
        label = "Asset Light"
    elif value <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return value, label


def fcf_conversion_rate(fcf, operating_profit):
    """
    FCF Conversion Rate = FCF / Operating Profit * 100
    """
    if operating_profit == 0:
        return None

    return (fcf / operating_profit) * 100


def get_sign(value):
    if value > 0:
        return "+"
    if value < 0:
        return "-"
    return "0"


def capital_allocation_pattern(cfo, cfi, cff, high_cfo_quality=False):
    """
    Classifies capital allocation pattern based on CFO, CFI, CFF signs.
    """

    cfo_sign = get_sign(cfo)
    cfi_sign = get_sign(cfi)
    cff_sign = get_sign(cff)

    if cfo_sign == "+" and cfi_sign == "-" and cff_sign == "-":
        if high_cfo_quality:
            return cfo_sign, cfi_sign, cff_sign, "Shareholder Returns"
        return cfo_sign, cfi_sign, cff_sign, "Reinvestor"

    if cfo_sign == "+" and cfi_sign == "+" and cff_sign == "-":
        return cfo_sign, cfi_sign, cff_sign, "Liquidating Assets"

    if cfo_sign == "-" and cfi_sign == "+" and cff_sign == "+":
        return cfo_sign, cfi_sign, cff_sign, "Distress Signal"

    if cfo_sign == "-" and cfi_sign == "-" and cff_sign == "+":
        return cfo_sign, cfi_sign, cff_sign, "Growth Funded by Debt"

    if cfo_sign == "+" and cfi_sign == "+" and cff_sign == "+":
        return cfo_sign, cfi_sign, cff_sign, "Cash Accumulator"

    if cfo_sign == "-" and cfi_sign == "-" and cff_sign == "-":
        return cfo_sign, cfi_sign, cff_sign, "Pre-Revenue"

    if cfo_sign == "+" and cfi_sign == "-" and cff_sign == "+":
        return cfo_sign, cfi_sign, cff_sign, "Mixed"

    return cfo_sign, cfi_sign, cff_sign, "Unclassified"