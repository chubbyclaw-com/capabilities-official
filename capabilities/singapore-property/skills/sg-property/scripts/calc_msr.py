#!/usr/bin/env python3
"""Mortgage Servicing Ratio (HDB / EC) calculator.

Reference: MAS / HDB MSR cap at 30% of gross monthly income for HDB flats
and ECs purchased directly from developers.
"""
import json
import sys


MSR_RATIO = 0.30


def pv_annuity(monthly_payment, monthly_rate, months):
    if monthly_payment <= 0:
        return 0.0
    if monthly_rate == 0:
        return monthly_payment * months
    return monthly_payment * (1 - (1 + monthly_rate) ** -months) / monthly_rate


def calc(income, tenure_years, stress_rate_pct):
    capacity = max(0.0, MSR_RATIO * income)
    monthly_rate = (stress_rate_pct / 100) / 12
    max_loan = pv_annuity(capacity, monthly_rate, tenure_years * 12)
    return {
        "max_monthly_payment": round(capacity, 2),
        "max_loan": round(max_loan, 2),
        "msr_ratio": MSR_RATIO,
        "stress_rate": stress_rate_pct,
        "tenure_years": tenure_years,
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as e:
        sys.stderr.write(json.dumps({"error": "invalid JSON", "detail": str(e)}) + "\n")
        return 2
    missing = [f for f in ("monthly_income", "loan_tenure") if f not in payload]
    if missing:
        sys.stderr.write(json.dumps({"error": "missing required fields", "fields": missing}) + "\n")
        return 2
    sys.stdout.write(json.dumps(calc(
        float(payload["monthly_income"]),
        int(payload["loan_tenure"]),
        float(payload.get("stress_rate", 4.0)),
    ), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
