# Policy calculator reference

Every script reads JSON on stdin and writes JSON on stdout. Exit 0 on
success, 2 on input error. Each script's docstring records the policy
revision date — when policy changes, edit the script and bump the date.

## Common contract

```bash
echo '{...}' | python3 scripts/<calc_script>.py
```

Output always includes a `policy_date` (where applicable) and a structured
`breakdown` or `assumptions` block. Show these to the user — they want to
see how the number was derived.

## calc_bsd.py — Buyer's Stamp Duty

**Input:**
```json
{ "purchase_price": 1500000 }
```

**Output:**
```json
{
  "amount": 44600,
  "breakdown": [
    { "slab_sgd": 180000, "rate": 0.01, "amount_sgd": 1800 }
  ],
  "policy_date": "2023-02-15"
}
```

Tiered residential rates: 1% / 2% / 3% / 4% / 5% / 6% on price slabs of
180k / 180k / 640k / 500k / 1.5m / remainder.

## calc_absd.py — Additional Buyer's Stamp Duty

**Input:**
```json
{
  "nationality": "SC | PR | FTA | Foreign",
  "marital_status": "single | married",
  "spouse_nationality": "SC | PR | FTA | Foreign",
  "owned_count": 0,
  "purchase_price": 1500000
}
```

**Output:**
```json
{
  "rate": 0.20,
  "amount": 300000,
  "bracket": "SC",
  "fta_exempt": false,
  "refund_eligible": true,
  "breakdown": [],
  "notes": "...",
  "policy_date": "2023-04-27"
}
```

Brackets:

| Buyer | 1st | 2nd | 3rd+ |
|-------|-----|-----|------|
| SC    | 0%  | 20% | 30%  |
| PR    | 5%  | 30% | 35%  |
| Foreign | 60% | 60% | 60% |

FTA nationals (US, IS, LI, NO, CH) are treated as SC. Joint purchase uses
the higher-bracket party. SC married couples upgrading qualify for refund
within 6 months of selling their first matrimonial home.

## calc_ssd.py — Seller's Stamp Duty

**Input:**
```json
{ "purchase_date": "2024-06-01", "sale_date": "2026-04-01", "sale_price": 1000000 }
```

Holding period rates (for residential bought on/after 11 Mar 2017):

| Held | Rate |
|------|------|
| ≤ 1 yr | 12% |
| 1–2 yr | 8% |
| 2–3 yr | 4% |
| > 3 yr | none |

Output `applies: false` when held more than 3 years.

## calc_tdsr.py — Total Debt Servicing Ratio

**Input:**
```json
{
  "monthly_income": 18000,
  "monthly_debt": 2500,
  "loan_tenure": 30,
  "stress_rate": 4.0
}
```

`stress_rate` defaults to 4.0% (MAS medium-term floor). Returns
`max_monthly_payment = max(0, 0.55 × income − debt)` and the present-value
maximum loan over `loan_tenure` years.

## calc_msr.py — Mortgage Servicing Ratio (HDB / EC)

**Input:**
```json
{ "monthly_income": 10000, "loan_tenure": 25, "stress_rate": 4.0 }
```

Caps payments at 30% of gross income. Same PV math as TDSR.

## calc_rental_yield.py

**Input:**
```json
{
  "annual_rent": 72000,
  "purchase_price": 1500000,
  "maintenance_annual": 4800,
  "property_tax_annual": 4000
}
```

Returns gross and net yield (decimals; 0.048 = 4.8%).

## calc_holding_cost.py

**Input:**
```json
{
  "mortgage_monthly": 4000,
  "maintenance_monthly": 400,
  "property_tax_annual": 3000,
  "income_tax_annual": 0
}
```

Returns `monthly_cost` and `annual_cost` plus a `components` breakdown.

## calc_breakeven.py

**Input:**
```json
{
  "purchase_price": 1000000,
  "selling_costs_pct": 0.05,
  "growth_rate_annual": 0.02
}
```

Returns `breakeven_years` such that `(1+g)^t × (1 - selling_pct) ≥ 1`.
If growth is zero or negative, returns `breakeven_years: null` with a
reason.

## When inputs are uncertain

Use a conservative assumption ("假设月收入 15000 / 持有 2 年 / 未持其他房产")
in the call, label clearly to the user, and **do not** persist that
assumption to memory.
