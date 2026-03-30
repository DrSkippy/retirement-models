import argparse
from datetime import timedelta

import numpy as np
import pandas as pd

# Default values
current_date = pd.to_datetime("2025-09-01")


# Function to calculate extra principal needed with lump sum option
def calculate_extra_principal(balance, monthly_pmt, rate, months, lump_sum=0):
    """Calculate extra principal needed to pay off loan in specified months with optional lump sum"""
    if months <= 0:
        return 0, 0, 0, 0

    # Apply lump sum payment
    remaining_balance = balance - lump_sum

    # Calculate required monthly payment to pay off in specified months
    required_payment = remaining_balance * (rate * (1 + rate) ** months) / ((1 + rate) ** months - 1)

    # Extra principal needed
    extra_principal = required_payment - monthly_pmt

    # Calculate total interest saved
    # Original scenario: continue with current payment
    original_balance = balance
    original_total_interest = 0
    temp_balance = original_balance
    while temp_balance > 0:
        interest = temp_balance * rate
        principal = monthly_pmt - interest
        original_total_interest += interest
        temp_balance -= principal
        if temp_balance <= 0:
            break

    # New scenario: with lump sum and extra principal
    new_total_interest = 0
    temp_balance = remaining_balance
    for _ in range(months):
        interest = temp_balance * rate
        principal = required_payment - interest
        new_total_interest += interest
        temp_balance -= principal
        if temp_balance <= 0:
            break

    interest_saved = original_total_interest - new_total_interest

    return extra_principal, required_payment, interest_saved, remaining_balance


def create_amortization_schedule(current_balance, total_payment, monthly_rate, current_date):
    # Create amortization schedule
    schedule = []
    remaining_balance = current_balance
    current_dt = current_date
    month = 1

    while remaining_balance > 0 and month <= 120:
        # Calculate interest for the month
        interest_payment = remaining_balance * monthly_rate

        # Calculate principal payment (regular payment minus interest)
        principal_payment = total_payment - interest_payment

        # Ensure we don't pay more than remaining balance
        if principal_payment > remaining_balance:
            principal_payment = remaining_balance
            total_payment = principal_payment + interest_payment

        # Update remaining balance
        remaining_balance -= principal_payment

        # Add to schedule
        schedule.append({
            'Month': month,
            'Payment': total_payment,
            'Principal': principal_payment,
            'Interest': interest_payment,
            'Remaining Balance': max(0, remaining_balance),
            'Date': current_dt.strftime('%Y-%m-%d')
        })

        # Move to next month
        month += 1
        current_dt = current_dt + timedelta(days=30)  # Approximate month

    # Convert to DataFrame
    df_schedule = pd.DataFrame(schedule)

    # Return the amortization schedule
    return df_schedule[['Month', 'Payment', 'Principal', 'Interest', 'Remaining Balance']]


if "__main__" == __name__:
    parser = argparse.ArgumentParser(description="Mortgage Adjustment Calculator")
    parser.add_argument("--current_balance", type=float, default=303318.79,
                        help="Current mortgage balance (default: 303318.79)")
    parser.add_argument("--monthly_payment", type=float, default=1405.25,
                        help="Current monthly payment (default: 1405.25)")
    parser.add_argument("--annual_rate", type=float, default=0.02875,
                        help="Annual interest rate as decimal (default: 0.02875)")
    parser.add_argument("--lump_sum", type=float, default=0, help="Lump sum payment (default: 0)")
    parser.add_argument("--target_date", type=str, default="2035-09-01",
                        help="Target payoff date (default: 2035-09-01)")
    args = parser.parse_args()

    current_balance = args.current_balance
    monthly_payment = args.monthly_payment
    annual_rate = args.annual_rate
    lump_sum = args.lump_sum
    target_date = pd.to_datetime(args.target_date)

    # Calculate monthly interest rate
    monthly_rate = annual_rate / 12

    # Calculate months between current date and target date
    months_to_payoff = (target_date.year - current_date.year) * 12 + (target_date.month - current_date.month)

    # Calculate extra principal needed
    extra_principal, total_payment, interest_saved, new_balance = calculate_extra_principal(
        current_balance, monthly_payment, monthly_rate, months_to_payoff, lump_sum
    )

    # Return results as a DataFrame
    results = pd.DataFrame({
        'Metric': ['Lump Sum Payment', 'New Loan Balance', 'Extra Principal Needed', 'Total Monthly Payment',
                   'Months to Payoff', 'Total Interest Saved'],
        'Value': [lump_sum, new_balance, extra_principal, total_payment, months_to_payoff, interest_saved]
    })

    print(results)

    # Create amortization schedule
    amortization_schedule = create_amortization_schedule(current_balance - lump_sum, total_payment, monthly_rate,
                                                         current_date)
    print(amortization_schedule)
