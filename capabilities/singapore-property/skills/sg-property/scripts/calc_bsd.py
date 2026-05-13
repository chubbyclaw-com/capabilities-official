#!/usr/bin/env python3
"""Buyer's Stamp Duty calculator.

Reference: IRAS BSD rates effective 15 Feb 2023.
https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/buyer's-stamp-duty-(bsd)

Tiered rates on residential property purchase price:
  first 180,000     1%
  next  180,000     2%
  next  640,000     3%
  next  500,000     4%
  next  1,500,000   5%
  remainder         6%
"""
import json
import sys


TIERS = [
    (180_000, 0.01),
    (180_000, 0.02),
    (640_000, 0.03),
    (500_000, 0.04),
    (1_500_000, 0.05),
    (None, 0.06),
]


def calc(price: float) -> dict:
    remaining = price
    breakdown = []
    total = 0.0
    for cap, rate in TIERS:
        if remaining <= 0:
            break
        slab = remaining if cap is None else min(remaining, cap)
        amount = slab * rate
        breakdown.append({"slab_sgd": slab, "rate": rate, "amount_sgd": round(amount, 2)})
        total += amount
        remaining -= slab
    return {"amount": round(total, 2), "breakdown": breakdown, "policy_date": "2023-02-15"}


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as e:
        sys.stderr.write(json.dumps({"error": "invalid JSON", "detail": str(e)}) + "\n")
        return 2
    price = payload.get("purchase_price")
    if price is None or not isinstance(price, (int, float)) or price < 0:
        sys.stderr.write(json.dumps({"error": "purchase_price must be a non-negative number",
                                     "field": "purchase_price"}) + "\n")
        return 2
    sys.stdout.write(json.dumps(calc(float(price)), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
