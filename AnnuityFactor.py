
STATE_PENSION_2025 = (230.25/7)*365
STATE_PENSION_2026 = 12500

state_pension = STATE_PENSION_2026

def r_real(r_growth, r_inflation):
    """Calculate the real interest rate."""
    return (1 + r_growth) / (1 + r_inflation) - 1

def annuity_factor(real_growth_rate, n_years):
    """Calculate the annuity factor given growth rate, inflation rate, and number of years."""
    if real_growth_rate == 0:
        return n_years
    return (1 -  (1 + real_growth_rate) ** (-n_years)) / real_growth_rate

def period_annuity_factor(real_growth_rate, n_start, n_end):
    """Payments to be drawn from the pot in periods n_start to n_end."""
    if n_start >= n_end:
        raise ValueError("n_start must be less than n_end")
    if n_start < 0 or n_end < 0:
        raise ValueError("n_start and n_end must be non-negative")
    if n_start == 1:
        return annuity_factor(real_growth_rate, n_end)

    return annuity_factor(real_growth_rate, n_end) - annuity_factor(real_growth_rate, n_start-1)

def annual_payment_in_arrears(real_growth_rate, n_years, present_value):
    """Calculate the annual payment for an annuity, taking 2 state pensions into account."""

    af_1_3 = period_annuity_factor(real_growth_rate, 1, 3)
    # print(f"Period Annuity Factor (Years 1 to 3): {af_1_3:.4f}")

    af_4_5 = period_annuity_factor(real_growth_rate, 4, 5)
    # print(f"Period Annuity Factor (Years 4 to 5): {af_4_5:.4f}")

    af_6_end = period_annuity_factor(real_growth_rate, 6, n_years)
    # print(f"Period Annuity Factor (Years 6 to {n_years}): {af_6_end:.4f}")

    return (present_value + af_4_5*state_pension + af_6_end*state_pension*2)/annuity_factor(real_growth_rate, n_years)

def annuity_due_factor(real_growth_rate, n_years):
    """Calculate the annuity due factor given growth rate, inflation rate, and number of years."""
    if real_growth_rate == 0:
        return n_years
    return (1 -  (1 + real_growth_rate) ** (-n_years)) * (1 + real_growth_rate) / real_growth_rate

def period_annuity_due_factor(real_growth_rate, n_start, n_end):
    """Payments to be drawn from the pot in periods n_start to n_end."""
    if n_start >= n_end:
        raise ValueError("n_start must be less than n_end")
    if n_start < 0 or n_end < 0:
        raise ValueError("n_start and n_end must be non-negative")
    if n_start == 1:
        return annuity_due_factor(real_growth_rate, n_end)

    discount_factor = (1 + real_growth_rate) ** (n_start-1)

    return annuity_due_factor(real_growth_rate, n_end-n_start+1) / discount_factor

def annual_payment_in_advance(real_growth_rate, n_years, present_value):
    """Calculate the annual payment for an annuity, taking 2 state pensions into account."""

    af_1_3 = period_annuity_due_factor(real_growth_rate, 1, 3)
    # print(f"Period Annuity Factor (Years 1 to 3): {af_1_3:.4f}")

    af_4_5 = period_annuity_due_factor(real_growth_rate, 4, 5)
    # print(f"Period Annuity Factor (Years 4 to 5): {af_4_5:.4f}")

    af_6_end = period_annuity_due_factor(real_growth_rate, 6, n_years)
    # print(f"Period Annuity Factor (Years 6 to {n_years}): {af_6_end:.4f}")

    return (present_value + af_4_5*state_pension + af_6_end*state_pension*2)/(af_1_3 + af_4_5 + af_6_end)


if __name__ == '__main__':
    # Example usage
    r_growth = 0.05         # 5% growth rate for investments
    r_inflation = 0.035     # 3.5% inflation rate
    n_years = 29            # Number of years pot must last
    pot_size = 1700000      # Total pot size

    real_growth_rate = r_real(r_growth, r_inflation)
    print(f"Real Growth Rate: {real_growth_rate:.5f}")
    
    for n_years in (3,6,29):
        factor = annuity_factor(real_growth_rate, n_years)
        print(f"Annuity Factor: {n_years} : {factor:.5f}")
        factor = annuity_due_factor(real_growth_rate, n_years)
        print(f"Annuity Due Factor: {n_years} : {factor:.5f}")

    payment = annual_payment_in_arrears(real_growth_rate, n_years, pot_size)
    print(f"Annual Payment (arrears): {n_years} : {payment:.5f}")

    payment = annual_payment_in_advance(real_growth_rate, n_years, pot_size)
    print(f"Annual Payment (advance): {n_years} : {payment:.5f}")

    exit(0)

    print(f"Growth %,Inflation %,Payment")
    for r_growth in range(3, 9):
        for r_inflation in range(2, 8):
            real_growth_rate = r_real(r_growth/100, r_inflation/100)
            payment = annual_payment_in_arrears(real_growth_rate, n_years, pot_size)
            print(f"{r_growth},{r_inflation},{payment:.2f}")

