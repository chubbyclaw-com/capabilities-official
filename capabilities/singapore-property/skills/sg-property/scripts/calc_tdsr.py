#!/usr/bin/env python3
"""Total Debt Servicing Ratio calculator.

Reference: MAS Notice 645 (TDSR), 55% threshold; 4% medium-term floor as
stress rate (effective Sep 2022).

max_monthly_payment = max(0, 0.55 × monthly_income − monthly_debt)
max_loan = PV of an annuity at stress_rate over loan_tenure years.
"""
import json
import sys


TDSR_RATIO = 0.55


def pv_annuity(monthly_payment, monthly_rate, months):
    if monthly_payment <= 0:
        return 0.0
    if monthly_rate == 0:
        return monthly_payment * months
    return monthly_payment * (1 - (1 + monthly_rate) ** -months) / monthly_rate


def calc(income, debt, tenure_years, stress_rate_pct):
    capacity = max(0.0, TDSR_RATIO * income - debt)
    monthly_rate = (stress_rate_pct / 100) / 12
    months = tenure_years * 12
    max_loan = pv_annuity(capacity, monthly_rate, months)
    return {
        "max_monthly_payment": round(capacity, 2),
        "max_loan": round(max_loan, 2),
        "tdsr_ratio": TDSR_RATIO,
        "stress_rate": stress_rate_pct,
        "tenure_years": tenure_years,
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as e:
        sys.stderr.write(json.dumps({"error": "invalid JSON", "detail": str(e)}) + "\n")
        return 2
    missing = [f for f in ("monthly_income", "monthly_debt", "loan_tenure") if f not in payload]
    if missing:
        sys.stderr.write(json.dumps({"error": "missing required fields", "fields": missing}) + "\n")
        return 2
    sys.stdout.write(json.dumps(calc(
        float(payload["monthly_income"]),
        float(payload["monthly_debt"]),
        int(payload["loan_tenure"]),
        float(payload.get("stress_rate", 4.0)),
    ), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
