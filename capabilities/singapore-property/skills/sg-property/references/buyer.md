# Buyer workflow

Use this reference when the user is shopping for property. Steps are
ordered, but skip ahead when the user already has the answer.

## 1. Eligibility & affordability

**Goal:** know how much they can spend and what taxes apply before browsing.

1. `python3 scripts/mem.py profile get` to see what is already known.
2. Ask only the missing fields needed for ABSD + TDSR (or MSR for
   HDB/EC):
   - `nationality`, `marital_status`, `spouse_nationality` (if married),
     `ownership.private_count` + `ownership.hdb_count`
   - `finance.monthly_income_sgd`, `finance.monthly_debt_sgd`,
     `finance.cpf_oa_sgd`, `finance.cash_available_sgd`
3. Persist each answer with `mem.py profile set` immediately.
4. Compute caps:
   - `echo '{...}' | python3 scripts/calc_tdsr.py` → max loan
   - For HDB / EC also run `calc_msr.py`
   - `calc_absd.py` for the duty on a hypothetical price
5. Affordable max purchase price ≈ max_loan + cash + CPF (subject to LTV /
   downpayment rules — flag those as separate constraints).

## 2. Needs collection

Ask the questions that narrow the search space:

- intent: first home, upgrade, investment, downsize?
- segment: private resale, new launch, HDB resale?
- bedrooms?
- preferred districts? avoid districts?
- school catchment (1km / 2km of which primary school)?
- commute target (work location, MRT walking minutes)?
- tenure preference (freehold / 99yr / either)?
- must-haves and nice-to-haves?

Persist via `mem.py profile set --patch '{"preferences":{...}}'`. Tag
unstable wishes (e.g. "near a park I like") into `notes`.

## 3. Project shortlist

Call `sgprop_search_projects` with the filters that matter most. Common
combos:

```
sgprop_search_projects --segment private --district 15,16 \
  --max_psf 2200 --bedrooms 3,4 --tenure freehold \
  --near_school_km 1 --school_name "Nanyang Primary"
```

**Result display rule (HARD):** After receiving results, immediately
partition by `status` before composing your reply:

1. **Upcoming / new launch first** — any project with `status` of
   `upcoming`, `new_launch`, or `preview` must appear in its own
   section at the top of the reply, labelled clearly (e.g.
   "即将推出 / New launches nearby"). Never bury these in a combined
   table with completed projects.
2. **Completed / resale second** — list in a separate section below.
3. **If no upcoming projects found**, explicitly state that fact so the
   user knows you checked. Do not stay silent on this.

This rule fires on every `sgprop_search_projects` call, including
school-catchment and supply-outlook searches. The user's
highest-value information is usually the upcoming project they do not
yet know about — surface it immediately.

For each candidate the user wants to track, add it:

```bash
python3 scripts/mem.py candidates add --data '{
  "project_name": "Stirling Residences",
  "address": "Stirling Rd",
  "stage": "shortlist",
  "asking_price_sgd": 2350000
}'
```

## 4. Candidate deep dive

Per candidate:

1. `sgprop_project_report --project "..."` — full meta, recent transactions,
   unit mix, maintenance, tenure, nearby supply, new launch progress.
2. `sgprop_location_context --address "..."` — schools, MRT, amenities,
   master plan.
3. `sgprop_supply_outlook --near_address "..." --years_ahead 5` — flag
   potential supply pressure.

Update the candidate with what you learn:

```bash
python3 scripts/mem.py candidates update --id <cid> --patch '{
  "estimated_value_sgd": 2280000,
  "pros": ["1km Henry Park Pri", "MRT 7min"],
  "cons": ["west sun"]
}'
```

## 5. Valuation & negotiation

Pull comparable transactions:

```
sgprop_transactions --project "Stirling Residences" \
  --period_from 2024-01 --bedrooms 3 \
  --area_sqft_from 950 --area_sqft_to 1050 \
  --floor_from 15 --floor_to 22
```

Report median PSF / price for the comparable cohort, flag any outliers.
Suggest an offer relative to median (e.g. "median PSF 2,100 → 980 sqft ≈
$2.06m; current asking $2.35m looks ~12% above median").

Set `my_max_price_sgd` on the candidate after agreeing on the ceiling with
the user.

## 6. Risk dilligence

- Remaining lease — affects CPF usage and resale value. Flag if < 60 yrs
  remaining at intended exit.
- Maintenance fee level (from `sgprop_project_report.maintenance`).
- Future supply within 1 km (`sgprop_supply_outlook`) — too many launches
  near completion = price pressure.
- Master plan zoning changes (`sgprop_location_context.master_plan`) —
  could be upside (rezoning to higher GFA) or downside (high-rise blocking
  view).

## 7. Tax & holding-cost summary

Once the user is serious about an offer:

- `calc_bsd.py` for BSD
- `calc_absd.py` for ABSD (use the user's actual ownership count)
- Lawyer fees (~$2.5–3k for resale) and valuation fee (~$300–500)
- `calc_holding_cost.py` for monthly carry
- `calc_breakeven.py` for "how long until I'd recoup costs at X% growth"

Show all components, then a single bottom-line "all-in cost over 5 years".

## 8. Stage advancement

When the user views, makes an offer, or closes:

```bash
python3 scripts/mem.py candidates advance-stage --id <cid>
# or, to jump:
python3 scripts/mem.py candidates advance-stage --id <cid> --stage offered
```

Drop a note for context:

```bash
python3 scripts/mem.py notes append --target candidates --id <cid> \
  --text "viewed 2026-05-10; agent quoted $2.32m floor"
```

## Common pitfalls to flag to the user

- Foreigners can only buy specific landed types (Sentosa Cove) and some
  condos — verify before raising hopes.
- ABSD is paid up-front; refund (where eligible) takes 6 months *after*
  selling first matrimonial home.
- LTV: 75% for first loan, drops to 45% / 25% for second / third —
  affects cash + CPF requirement.
- New launch progressive payments stretch over years; the user's TDSR
  needs to clear at TOP, not just at booking.
