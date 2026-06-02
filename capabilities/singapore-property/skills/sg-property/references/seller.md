# Seller workflow

Use this reference when the user wants to value, list, or sell their place.

## 1. Capture the holding

`MemorySearch("sgprop:holding")` — see what's known. If a hit comes back,
`MemoryGet(id)` to read the stored fields. If empty or the user is asking
about a different unit, ask:

- address (block + unit number)
- type: private / hdb
- purchase date and price
- current loan outstanding
- remaining lease years
- last renovation year
- intent: `sell` (for an active listing) or `enbloc_wait` / `hold` (for
  passive exit planning)

Persist by writing a new `sgprop:holding` record:

```
MemoryWrite(value="""sgprop:holding | Marine Blue #18-05

type: private
purchase_date: 2019-08
purchase_price_sgd: 1380000
current_loan_sgd: 720000
remaining_lease_years: 86
intent: sell

```json
{"address":"Marine Blue #18-05","type":"private","purchase_date":"2019-08",
 "purchase_price_sgd":1380000,"current_loan_sgd":720000,
 "remaining_lease_years":86,"intent":"sell"}
```
""", tags=["sgprop:holding", "Marine Blue #18-05"])
```

(Full envelope shape and `tags` in `references/memory-conventions.md`.)

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
  if not available, note the gap to the user). Apply SKILL.md SOP §9
  display rule — upcoming launches in the district are the most important
  competitive signal and must be surfaced first.
- Market temperature: count of `sgprop_transactions` in the last 3 / 6 /
  12 months. Cooling absorption + many launches → price below median.
- Suggest one of: aggressive (set 2-3% above median for negotiation
  buffer), market (median), quick (2-5% below median).

Persist the chosen `listing_price_sgd` (and the rest of the `sales`
substructure) with the update protocol: `MemorySearch("sgprop:holding
<address>")` → `MemoryGet(id)` → merge `sales.listing_price_sgd` →
`MemoryUpdate(id, <new envelope>)` (in place, same `id`).

## 5. Timing decision

When the user asks "now or wait":

- Future supply: `sgprop_supply_outlook --near_address "<addr>"
  --years_ahead 2` — too many TOPs in the next 12-18 months = sell first.
  Apply SKILL.md SOP §9 — name any upcoming projects in the results
  explicitly; state if none found.
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

Once the unit goes live, treat events as independent records — do **not**
keep mutating a packed `sales.viewings[]` / `sales.offers[]` array on the
holding.

Set the listing live by updating the holding's `sales.status` and
`sales.listed_date` via the update protocol:

`MemorySearch("sgprop:holding Marine Blue #18-05")` → `MemoryGet(id)` →
merge `sales.listed_date = "2026-05-09"`, `sales.status = "live"` →
`MemoryUpdate(id, <new envelope>)` (in place, same `id`).

Then, for each viewing / offer:

```
MemoryWrite(value="""sgprop:viewing | Marine Blue #18-05 | 2026-05-12

outcome: interested
attendees: 2

```json
{"parent_kind":"holding","parent_id":"Marine Blue #18-05",
 "date":"2026-05-12","outcome":"interested","attendees":2}
```
""", tags=["sgprop:viewing", "Marine Blue #18-05"])
```

```
MemoryWrite(value="""sgprop:offer | Marine Blue #18-05 | 2026-05-15

amount_sgd: 1830000
status: rejected

```json
{"parent_kind":"holding","parent_id":"Marine Blue #18-05",
 "date":"2026-05-15","amount_sgd":1830000,"status":"rejected"}
```
""", tags=["sgprop:offer", "Marine Blue #18-05"])
```

To review the listing history: `MemorySearch("sgprop:viewing Marine Blue
#18-05")` and `MemorySearch("sgprop:offer Marine Blue #18-05")`, then
`MemoryGet` each hit and assemble the timeline in the reply. Independent
records keep appends conflict-free.

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
