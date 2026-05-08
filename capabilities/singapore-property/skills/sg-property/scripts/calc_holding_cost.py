#!/usr/bin/env python3
"""Monthly + annual holding-cost calculator."""
import json
import sys


def calc(mortgage_m, maint_m, tax_y, income_tax_y):
    monthly = mortgage_m + maint_m + tax_y / 12 + income_tax_y / 12
    return {
        "monthly_cost": round(monthly, 2),
        "annual_cost": round(monthly * 12, 2),
        "components": {
            "mortgage_monthly": mortgage_m,
            "maintenance_monthly": maint_m,
            "property_tax_monthly": round(tax_y / 12, 2),
            "income_tax_monthly": round(income_tax_y / 12, 2),
        },
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as e:
        sys.stderr.write(json.dumps({"error": "invalid JSON", "detail": str(e)}) + "\n")
        return 2
    required = ("mortgage_monthly", "maintenance_monthly", "property_tax_annual")
    missing = [f for f in required if f not in payload]
    if missing:
        sys.stderr.write(json.dumps({"error": "missing required fields", "fields": missing}) + "\n")
        return 2
    sys.stdout.write(json.dumps(calc(
        float(payload["mortgage_monthly"]),
        float(payload["maintenance_monthly"]),
        float(payload["property_tax_annual"]),
        float(payload.get("income_tax_annual", 0)),
    ), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
