# Seller workflow

Use this reference when the user wants to value, list, or sell their place.

## 1. Capture the holding

`python3 scripts/mem.py holdings list` — see what's known. If empty or the
user is asking about a different unit, ask:

- address (block + unit number)
- type: private / hdb
- purchase date and price
- current loan outstanding
- remaining lease years
- last renovation year
- intent: `sell` (for an active listing) or `enbloc_wait` / `hold` (for
  passive exit planning)

Persist:

```bash
python3 scripts/mem.py holdings add --data '{
  "address": "Marine Blue #18-05",
  "type": "private",
  "purchase_date": "2019-08",
  "purchase_price_sgd": 1380000,
  "current_loan_sgd": 720000,
  "remaining_lease_years": 86,
  "intent": "sell"
}'
```

## 2. CMA valuation

Pull two cohorts of comparable sales:

1. **Same project**: `sgprop_project_report --project "<name>" --sections transactions`
   — closest comparables (same stack / floor / unit type).
2. **Nearby competing projects**: `sgprop_transactions` filtered by
   district + bedrooms + size band.

Adjust for the unit's specifics:

- **Stack premium / discount**: corner stack, dual-key, west sun, dual
  facing — note ±2-5%.
- **Floor**: each floor differential is typically 0.3-0.5% PSF in the
  same stack.
- **Renovation**: tasteful recent reno = +3-5%, dated = -3-5%.
- **Lease decay**: every year off the 99-yr lease shaves resale value;
  reference the "Bala's curve" rule of thumb (≈ 0.5-1% / yr depending on
  remaining lease).

Output a price band (low / median / high) with the comparables that
support each end.

## 3. Sale-cost computation

- **SSD** (only if held < 3 years):
  ```bash
  echo '{"purchase_date":"2024-06-01","sale_date":"2026-05-01","sale_price":1880000}' \
    | python3 scripts/calc_ssd.py
  ```
- **Agent commission** (typically 2% private, 1% HDB seller): manually
  computed from the agreed sale price.
- **Lawyer fee** ~ $2.5–3k.
- **Loan prepayment penalty** if within lock-in: typically 1.5% of
  outstanding loan.

Net-to-hand:
```
sale_price - SSD - commission - lawyer - prepayment - outstanding_loan
```

Show this clearly to the user. If they're upgrading, the net is the cash
that funds the next purchase.

## 4. Pricing strategy

- Anchor on CMA median.
- Survey live competition: `sgprop_search_projects --district <d>
  --segment private` (active listings need an external listing platform —
  if not available, note the gap to the user).
- Market temperature: count of `sgprop_transactions` in the last 3 / 6 /
  12 months. Cooling absorption + many launches → price below median.
- Suggest one of: aggressive (set 2-3% above median for negotiation
  buffer), market (median), quick (2-5% below median).

Persist with `mem.py holdings update --id <id> --patch '{"sales":{"listing_price_sgd":...}}'`.

## 5. Timing decision

When the user asks "now or wait":

- Future supply: `sgprop_supply_outlook --near_address "<addr>"
  --years_ahead 2` — too many TOPs in the next 12-18 months = sell first.
- Mortgage rate trajectory and TDSR — fewer buyers can afford if rates
  rise.
- SSD window: if they bought < 3 years ago, often worth waiting out the
  SSD cliff (large savings).
- Personal cashflow / tax position.

Lay out the trade-off; do not push a binary decision.

## 6. En bloc potential

Only relevant for older private projects. Pull:

- `sgprop_location_context --address "..."` for the master plan zoning,
  GFA cap, and current building utilisation.
- Project age (from `sgprop_project_report.meta.top_year`).
- Tenure (freehold tends to be more attractive for redevelopment).

Heuristic: freehold + > 25 years old + GFA significantly below cap =
candidate. This is signal, not certainty — collective sales need 80%+
owner consent.

## 7. Listing tracker

When the unit goes live, update the `sales` substructure on every
material event:

```bash
python3 scripts/mem.py holdings update --id my-marine-blue --patch '{
  "sales": { "listed_date": "2026-05-09", "status": "live" }
}'

# log a viewing
python3 scripts/mem.py holdings update --id my-marine-blue --patch '{
  "sales": { "viewings": [{"date":"2026-05-12","outcome":"interested"}] }
}'

# log an offer
python3 scripts/mem.py holdings update --id my-marine-blue --patch '{
  "sales": { "offers": [{"date":"2026-05-15","amount":1830000,"status":"rejected"}] }
}'
```

(If the user wants the new viewing/offer *appended* and not overwritten,
do a `mem.py holdings get --id ...` first, merge in code, and pass the
full updated array.)

## 8. Upgrade chain

When `intent="upgrade"`:

- Remind the user of the **6-month ABSD remission window** for SC married
  couples: ABSD on the new place is refunded if you sell the old within
  6 months of buying.
- Sequencing: usually buy first → sell within 6 months, but stretches
  cashflow. Selling first → renting → buying avoids ABSD upfront but
  exposes them to rising prices.
- Connect to the buyer workflow (`references/buyer.md`) for the next
  property.

## Common pitfalls

- Don't compute SSD by hand — always run `calc_ssd.py`.
- Net-to-hand differs from gross sale price by 5-8% — make sure the user
  sees the breakdown before they price.
- "We bought at X" is sunk cost; don't anchor list price on it.
