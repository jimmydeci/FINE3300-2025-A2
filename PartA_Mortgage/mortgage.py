# Part 1: MortgagePayment class
# This module defines a class that computes Canadian mortgage payments
# for monthly, semi-monthly, bi-weekly, weekly, and accelerated payment schedules

from __future__ import annotations

class MortgagePayment:
    def __init__(self, quoted_rate_percent: float, amort_years: int, term_years: int | None = None):
        self.quoted_rate_percent = quoted_rate_percent
        self.amort_years = amort_years
        self.term_years = term_years if term_years is not None else amort_years

    def _ear_from_semiannual(self) -> float:
        # converts the percent rate user provides to a decimal
        j = self.quoted_rate_percent / 100
        # formula for converting semi annual rate to EAR
        return (1 + j/2) ** 2 - 1

    def _periodic_rate(self, payments_per_year: int) -> float:
        ear = self._ear_from_semiannual()
        # provides the per payment interest rate
        return (1 + ear) ** (1 / payments_per_year) - 1

    def _annuity_payment(self, principal: float, r: float, n: int) -> float:
        # takes 3 inputs: principal = amount borrowed, r = periodic interest rate, n = number of payments
        if r == 0:
            return principal / n  # If the interest is 0%, the formula would not work
        # Standard annuity formula for loans
        return principal * (r / (1 - (1 + r) ** (-n)))

    def payments(self, principal: float) -> tuple[float, float, float, float, float, float]:
        # Monthly
        r_m = self._periodic_rate(12)
        n_m = self.amort_years * 12
        monthly = self._annuity_payment(principal, r_m, n_m)

        # Semi-monthly (24/yr)
        r_sm = self._periodic_rate(24)
        n_sm = self.amort_years * 24
        semi_monthly = self._annuity_payment(principal, r_sm, n_sm)

        # Bi-weekly (26/yr)
        r_bw = self._periodic_rate(26)
        n_bw = self.amort_years * 26
        bi_weekly = self._annuity_payment(principal, r_bw, n_bw)

        # Weekly (52/yr)
        r_wk = self._periodic_rate(52)
        n_wk = self.amort_years * 52
        weekly = self._annuity_payment(principal, r_wk, n_wk)

        # Accelerated versions are defined relative to monthly
        accel_bi_weekly = monthly / 2
        accel_weekly = monthly / 4

        return (
            round(monthly, 2),
            round(semi_monthly, 2),
            round(bi_weekly, 2),
            round(weekly, 2),
            round(accel_bi_weekly, 2),
            round(accel_weekly, 2),
        )

    # === Added for Assignment 2 ===
    def _schedule(self, principal: float, payments_per_year: int, payment_amount: float, years_limit: int):
        """Build a DataFrame with Period, Starting Balance, Interest, Payment, Ending Balance."""
        import pandas as pd
        i = self._periodic_rate(payments_per_year)
        limit_years = max(1, min(years_limit, self.amort_years))
        nmax = limit_years * payments_per_year
        bal = float(principal)
        out, k = [], 0
        while bal > 1e-6 and k < nmax + 2:
            k += 1
            start = bal
            interest = start * i
            principal_comp = payment_amount - interest
            if principal_comp > start:
                principal_comp = start
                pay_eff = interest + principal_comp
            else:
                pay_eff = payment_amount
            bal = start - principal_comp
            out.append({
                "Period": k,
                "Starting Balance": round(start, 2),
                "Interest": round(interest, 2),
                "Payment": round(pay_eff, 2),
                "Ending Balance": round(bal, 2)
            })
        return pd.DataFrame(out)

    def schedules(self, principal: float, years: int | None = None):
        """Return six DataFrames (one per payment option)."""
        years_limit = years if years is not None else self.term_years
        years_limit = max(1, min(years_limit, self.amort_years))
        monthly, semi_monthly, bi_weekly, weekly, accel_bi_weekly, accel_weekly = self.payments(
            principal)
        return {
            "monthly":               self._schedule(principal, 12, monthly, years_limit),
            "semi-monthly":          self._schedule(principal, 24, semi_monthly, years_limit),
            "bi-weekly":             self._schedule(principal, 26, bi_weekly, years_limit),
            "weekly":                self._schedule(principal, 52, weekly, years_limit),
            "accelerated bi-weekly": self._schedule(principal, 26, accel_bi_weekly, years_limit),
            "accelerated weekly":    self._schedule(principal, 52, accel_weekly, years_limit)
        }
