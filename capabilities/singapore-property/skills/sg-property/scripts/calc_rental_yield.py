#!/usr/bin/env python3
"""Rental yield calculator (gross + net)."""
import json
import sys


def calc(rent, price, maint, tax):
    gross = rent / price
    net = (rent - maint - tax) / price
    return {
        "gross_yield": round(gross, 6),
        "net_yield": round(net, 6),
        "annual_rent": rent,
        "purchase_price": price,
        "annual_costs": round(maint + tax, 2),
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as e:
        sys.stderr.write(json.dumps({"error": "invalid JSON", "detail": str(e)}) + "\n")
        return 2
    missing = [f for f in ("annual_rent", "purchase_price") if f not in payload]
    if missing:
        sys.stderr.write(json.dumps({"error": "missing required fields", "fields": missing}) + "\n")
        return 2
    price = float(payload["purchase_price"])
    if price <= 0:
        sys.stderr.write(json.dumps({"error": "purchase_price must be > 0",
                                     "field": "purchase_price"}) + "\n")
        return 2
    sys.stdout.write(json.dumps(calc(
        float(payload["annual_rent"]),
        price,
        float(payload.get("maintenance_annual", 0)),
        float(payload.get("property_tax_annual", 0)),
    ), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
