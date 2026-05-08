#!/usr/bin/env python3
"""Additional Buyer's Stamp Duty calculator.

Reference: IRAS ABSD rates effective 27 Apr 2023.
https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/additional-buyer's-stamp-duty-(absd)

Buyer profile         | 1st  | 2nd  | 3rd+
Singapore Citizen     | 0%   | 20%  | 30%
Permanent Resident    | 5%   | 30%  | 35%
Foreigner             | 60%  | 60%  | 60%

FTA nationals are treated as Singapore Citizens (US, IS, LI, NO, CH).
For joint purchases, ABSD applies on the highest-bracket buyer.
SC married couples buying a matrimonial home together qualify for full
ABSD remission. SC married couples upgrading qualify for refund within
6 months of selling their first home.
"""
import json
import sys


SC_RATES = [0.0, 0.20, 0.30]
PR_RATES = [0.05, 0.30, 0.35]
FOREIGN_RATE = 0.60
FTA_NATIONALITIES = {"FTA"}


def _bracket_rate(nationality, owned_count):
    if nationality in ("SC",) or nationality in FTA_NATIONALITIES:
        idx = min(owned_count, len(SC_RATES) - 1)
        return SC_RATES[idx], "SC"
    if nationality == "PR":
        idx = min(owned_count, len(PR_RATES) - 1)
        return PR_RATES[idx], "PR"
    return FOREIGN_RATE, "Foreign"


def calc(payload: dict) -> dict:
    nationality = payload["nationality"]
    spouse = payload.get("spouse_nationality")
    marital_status = payload.get("marital_status", "single")
    owned = int(payload["owned_count"])
    price = float(payload["purchase_price"])

    rate, bracket = _bracket_rate(nationality, owned)
    notes_parts = []
    breakdown = [{"party": "buyer", "nationality": nationality, "rate": rate}]

    if marital_status == "married" and spouse:
        srate, sbracket = _bracket_rate(spouse, owned)
        breakdown.append({"party": "spouse", "nationality": spouse, "rate": srate})
        if srate > rate:
            notes_parts.append(f"joint purchase: spouse ({spouse}) is higher bracket; ABSD applied at {srate:.0%}")
            rate = srate
            bracket = sbracket

    fta_exempt = nationality in FTA_NATIONALITIES
    refund_eligible = (
        marital_status == "married"
        and nationality == "SC"
        and (spouse == "SC" or spouse in FTA_NATIONALITIES)
        and owned >= 1
    )
    if refund_eligible:
        notes_parts.append("SC couple upgrading: ABSD refund within 6 months of selling first matrimonial home")

    amount = round(price * rate, 2)
    return {
        "rate": rate,
        "amount": amount,
        "bracket": bracket,
        "fta_exempt": fta_exempt,
        "refund_eligible": refund_eligible,
        "breakdown": breakdown,
        "notes": "; ".join(notes_parts),
        "policy_date": "2023-04-27",
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as e:
        sys.stderr.write(json.dumps({"error": "invalid JSON", "detail": str(e)}) + "\n")
        return 2
    missing = [f for f in ("nationality", "owned_count", "purchase_price") if f not in payload]
    if missing:
        sys.stderr.write(json.dumps({"error": "missing required fields", "fields": missing}) + "\n")
        return 2
    if payload["nationality"] not in ("SC", "PR", "FTA", "Foreign"):
        sys.stderr.write(json.dumps({"error": "nationality must be SC|PR|FTA|Foreign",
                                     "field": "nationality"}) + "\n")
        return 2
    sys.stdout.write(json.dumps(calc(payload), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
