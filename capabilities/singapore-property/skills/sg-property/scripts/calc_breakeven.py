#!/usr/bin/env python3
"""Break-even calculator: how many years before resale clears purchase costs."""
import json
import math
import sys


def calc(price, selling_pct, growth):
    if growth <= 0:
        return {
            "breakeven_years": None,
            "reason": "no growth or negative growth — never breaks even",
            "assumptions": {"selling_costs_pct": selling_pct, "growth_rate_annual": growth},
        }
    target = 1 / (1 - selling_pct)
    years = math.log(target) / math.log(1 + growth)
    return {
        "breakeven_years": round(years, 2),
        "assumptions": {
            "purchase_price": price,
            "selling_costs_pct": selling_pct,
            "growth_rate_annual": growth,
            "exit_target_price": round(price * target, 2),
        },
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as e:
        sys.stderr.write(json.dumps({"error": "invalid JSON", "detail": str(e)}) + "\n")
        return 2
    required = ("purchase_price", "selling_costs_pct", "growth_rate_annual")
    missing = [f for f in required if f not in payload]
    if missing:
        sys.stderr.write(json.dumps({"error": "missing required fields", "fields": missing}) + "\n")
        return 2
    sys.stdout.write(json.dumps(calc(
        float(payload["purchase_price"]),
        float(payload["selling_costs_pct"]),
        float(payload["growth_rate_annual"]),
    ), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
