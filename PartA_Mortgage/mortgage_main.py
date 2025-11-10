# Main program to run Assignment 2 Part A

import pandas as pd
import matplotlib.pyplot as plt
from mortgage import MortgagePayment


def plot_balances(schedules: dict, out_png: str):
    plt.figure(figsize=(9, 6))
    for name, df in schedules.items():
        plt.plot(df["Period"], df["Ending Balance"], label=name)
    plt.title("Loan Balance Decline (Six Payment Options)")
    plt.xlabel("Period")
    plt.ylabel("Ending Balance ($)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()


def run_mortgage():
    print("\n--- Mortgage Payments ---")
    principal = float(input("Enter the principal amount: "))
    rate = float(input("Enter the quoted annual interest rate (%): "))
    amort_years = int(input("Enter the amortization period (in years): "))
    term = int(input("Enter the mortgage term (in years): "))

    calc = MortgagePayment(rate, amort_years, term)
    payments = calc.payments(principal)

    print("\n--- Mortgage Payment Results ---")
    print(f"Monthly Payment: ${payments[0]:.2f}")
    print(f"Semi-monthly Payment: ${payments[1]:.2f}")
    print(f"Bi-weekly Payment: ${payments[2]:.2f}")
    print(f"Weekly Payment: ${payments[3]:.2f}")
    print(f"Rapid Bi-weekly Payment: ${payments[4]:.2f}")
    print(f"Rapid Weekly Payment: ${payments[5]:.2f}")

    # === Assignment 2 additions ===
    schedules = calc.schedules(principal, years=term)
    monthly_term_balance = schedules["monthly"]["Ending Balance"].iloc[-1]
    print(
        f"\nOutstanding balance after {term}-year term (monthly schedule): ${monthly_term_balance:,.2f}")

    # one Excel with six worksheets
    out_xlsx = "Loan_Payment_Schedules.xlsx"
    keep = ["Period", "Starting Balance",
            "Interest", "Payment", "Ending Balance"]
    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as w:
        for name, df in schedules.items():
            df[keep].to_excel(w, sheet_name=name.title()[:31], index=False)

    # one PNG with all 6 curves
    out_png = "Loan_Balance_Decline.png"
    plot_balances(schedules, out_png)

    print(f"\nSaved: {out_xlsx}")
    print(f"Saved: {out_png}")


if __name__ == "__main__":
    run_mortgage()
