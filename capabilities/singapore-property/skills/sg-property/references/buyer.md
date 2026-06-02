# Buyer workflow

Use this reference when the user is shopping for property. Steps are
ordered, but skip ahead when the user already has the answer.

## 1. Eligibility & affordability

**Goal:** know how much they can spend and what taxes apply before browsing.

1. `MemorySearch("sgprop:profile")` to see what is already known; if a hit
   comes back, `MemoryGet(id)` to read the stored fields.
2. Ask only the missing fields needed for ABSD + TDSR (or MSR for
   HDB/EC):
   - `nationality`, `marital_status`, `spouse_nationality` (if married),
     `ownership.private_count` + `ownership.hdb_count`
   - `finance.monthly_income_sgd`, `finance.monthly_debt_sgd`,
     `finance.cpf_oa_sgd`, `finance.cash_available_sgd`
3. Persist each answer immediately using the profile update protocol:
   `MemorySearch("sgprop:profile")` → `MemoryGet(id)` → merge →
   `MemoryUpdate(id, <new envelope>)` to overwrite in place. If no profile
   exists yet, just `MemoryWrite` a fresh `sgprop:profile` envelope (see
   `references/memory-conventions.md` for the shape and the full
   Search→Get→merge→`MemoryUpdate` protocol).
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

Persist by running the profile update protocol again (Search → Get →
merge new `preferences` block → `MemoryUpdate(id)`). Tag unstable wishes
(e.g. "near a park I like") into the profile's `notes` field, or write a
free-standing `sgprop:note` if it's verbose.

## 3. Project shortlist

Call `sgprop_search_projects` with the filters that matter most. Common
combos:

```
sgprop_search_projects --segment private --district 15,16 \
  --max_psf 2200 --bedrooms 3,4 --tenure freehold \
  --near_school_km 1 --school_name "Nanyang Primary"
```

For each candidate the user wants to track, write a `sgprop:candidate`
record:

```
MemoryWrite(value="""sgprop:candidate | Stirling Residences | 2026-05

address: Stirling Rd
stage: shortlist
asking_price_sgd: 2350000

```json
{"project_name":"Stirling Residences","address":"Stirling Rd",
 "stage":"shortlist","asking_price_sgd":2350000}
```
""", tags=["sgprop:candidate", "Stirling Residences"])
```

(Full envelope shape, `tags`, and identifier rules in
`references/memory-conventions.md`.)

## 4. Candidate deep dive

Per candidate:

1. `sgprop_project_report --project "..."` — full meta, recent transactions,
   unit mix, maintenance, tenure, nearby supply, new launch progress.
2. `sgprop_location_context --address "..."` — schools, MRT, amenities,
   master plan.
3. `sgprop_supply_outlook --near_address "..." --years_ahead 5` — flag
   potential supply pressure.

Update the candidate with what you learn using the update protocol:

1. `MemorySearch("sgprop:candidate Stirling Residences")` → grab the id
2. `MemoryGet(id)` → parse the JSON body
3. Merge `estimated_value_sgd`, `pros`, `cons` into the JSON
4. `MemoryUpdate(id, <new envelope>)` — in place, same `id`; omit `tags`
   (the identifier hasn't changed). Do **not** write a new record and delete
   the old one.

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

Set `my_max_price_sgd` on the candidate (via the update protocol) after
agreeing on the ceiling with the user.

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

Stage progresses along `shortlist → viewing_scheduled → viewed → offered
→ {declined | closed}`.

When the user views, makes an offer, or closes, advance the `stage` field
via the update protocol (Search → Get → merge `stage` → `MemoryUpdate(id)`).
Then, for the event itself, write an independent record:

- Viewing → `sgprop:viewing` (template in `references/memory-conventions.md`)
- Offer → `sgprop:offer`

Drop a free-text note as its own record:

```
MemoryWrite(value="""sgprop:note | candidate | Stirling Residences

text: viewed 2026-05-10; agent quoted $2.32m floor

```json
{"parent_kind":"candidate","parent_id":"Stirling Residences",
 "text":"viewed 2026-05-10; agent quoted $2.32m floor","date":"2026-05-10"}
```
""", tags=["sgprop:note", "Stirling Residences"])
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
