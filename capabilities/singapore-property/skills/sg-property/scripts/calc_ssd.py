#!/usr/bin/env python3
"""Seller's Stamp Duty calculator.

Reference: IRAS SSD rates for residential property bought on/after 11 Mar 2017.

Holding period (purchase → sale):
  ≤ 1 year      12%
  > 1, ≤ 2 yrs   8%
  > 2, ≤ 3 yrs   4%
  > 3 years      no SSD
"""
import json
import sys
from datetime import date


def _parse(s: str, field: str) -> date:
    try:
        if len(s) == 7:  # YYYY-MM
            s = s + "-01"
        return date.fromisoformat(s)
    except ValueError as e:
        sys.stderr.write(json.dumps({"error": f"invalid date {field}", "field": field,
                                     "detail": str(e)}) + "\n")
        sys.exit(2)


def calc(purchase: date, sale: date, price: float) -> dict:
    days = (sale - purchase).days
    years = days / 365.25
    if years > 3:
        return {"applies": False, "rate": 0, "amount": 0,
                "holding_years": round(years, 2),
                "reason": "no SSD: held more than 3 years",
                "policy_date": "2017-03-11"}
    if years <= 1:
        rate = 0.12
    elif years <= 2:
        rate = 0.08
    else:
        rate = 0.04
    return {
        "applies": True,
        "rate": rate,
        "amount": round(price * rate, 2),
        "holding_years": round(years, 2),
        "policy_date": "2017-03-11",
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as e:
        sys.stderr.write(json.dumps({"error": "invalid JSON", "detail": str(e)}) + "\n")
        return 2
    missing = [f for f in ("purchase_date", "sale_date", "sale_price") if f not in payload]
    if missing:
        sys.stderr.write(json.dumps({"error": "missing required fields", "fields": missing}) + "\n")
        return 2
    purchase = _parse(payload["purchase_date"], "purchase_date")
    sale = _parse(payload["sale_date"], "sale_date")
    price = float(payload["sale_price"])
    sys.stdout.write(json.dumps(calc(purchase, sale, price), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
