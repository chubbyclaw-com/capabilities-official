# Memory schema reference

Storage root: `~/.config/sgprop/` (override with `SGPROP_HOME`). Files are
written with `0600` perms. The `mem.py` CLI is the only sanctioned writer.
**Never `Write` these files directly.**

Schema policy: **lenient**. Unknown fields are accepted with a stderr
warning. Known-field type mismatches are rejected (exit 2).

## profile.json — single object

```jsonc
{
  "identity": {
    "nationality": "SC | PR | FTA | Foreign",
    "marital_status": "single | married",
    "spouse_nationality": "SC | PR | FTA | Foreign",
    "household_size": 3,
    "children": [{ "age": 6, "school_pref": "Nanyang Primary" }]
  },
  "finance": {
    "monthly_income_sgd": 18000,
    "household_income_sgd": 28000,
    "monthly_debt_sgd": 2500,
    "cpf_oa_sgd": 180000,
    "cash_available_sgd": 250000
  },
  "ownership": {
    "private_count": 0,
    "hdb_count": 1,
    "owns_overseas": false
  },
  "preferences": {
    "budget_max_sgd": 2500000,
    "bedrooms": [3, 4],
    "districts_prefer": ["15", "16"],
    "districts_avoid": ["22"],
    "segment": ["resale", "new_launch"],
    "tenure_pref": "freehold | any",
    "must_haves": ["near MRT 10min", "1km top primary school"],
    "work_location": "Raffles Place"
  },
  "intent": "first_home | upgrade | investment | downsize",
  "notes": "free text"
}
```

All fields optional. `notes` is the catch-all for vague info.

### CLI examples

```bash
python3 scripts/mem.py profile get
python3 scripts/mem.py profile set --patch '{"finance":{"monthly_income_sgd":18000}}'
python3 scripts/mem.py profile clear --field "finance.cpf_oa_sgd"
```

---

## holdings.json — array of properties

```jsonc
{
  "properties": [
    {
      "id": "my-marine-blue",
      "address": "Marine Blue #18-05",
      "type": "private | hdb",
      "purchase_date": "2019-08",
      "purchase_price_sgd": 1380000,
      "current_loan_sgd": 720000,
      "remaining_lease_years": 86,
      "renovated_year": 2020,
      "intent": "sell | hold | enbloc_wait",
      "sales": {
        "listing_price_sgd": 1880000,
        "listed_date": "2026-04-20",
        "price_history": [{ "date": "2026-04-20", "price": 1900000 }],
        "viewings": [{ "date": "2026-05-02", "outcome": "interested" }],
        "offers": [{ "date": "2026-05-05", "amount": 1830000, "status": "rejected" }],
        "status": "live | offer_received | option_exercised | closed"
      },
      "notes": "free text"
    }
  ]
}
```

`sales` only present when `intent="sell"`. `id` auto-generated from address
if you don't provide one.

### CLI examples

```bash
python3 scripts/mem.py holdings list
python3 scripts/mem.py holdings get --id my-marine-blue
python3 scripts/mem.py holdings add --data '{"address":"...","type":"private","purchase_price_sgd":1380000}'
python3 scripts/mem.py holdings update --id my-marine-blue --patch '{"sales":{"status":"live"}}'
python3 scripts/mem.py holdings remove --id my-marine-blue
```

---

## candidates.json — properties under evaluation

```jsonc
{
  "candidates": [
    {
      "id": "stirling-residences-2026-05",
      "project_name": "Stirling Residences",
      "address": "Stirling Rd",
      "stage": "shortlist | viewing_scheduled | viewed | offered | declined | closed",
      "viewed_dates": ["2026-05-10"],
      "unit_details": { "stack": "05", "floor": 18, "size_sqft": 980, "bedrooms": 3 },
      "asking_price_sgd": 2350000,
      "my_max_price_sgd": 2200000,
      "estimated_value_sgd": 2280000,
      "pros": ["1km Henry Park Pri", "Queenstown MRT 7min"],
      "cons": ["west sun", "high maintenance fee"],
      "compared_with": ["other-candidate-id"],
      "notes": "free text"
    }
  ]
}
```

Stage advances along: `shortlist → viewing_scheduled → viewed → offered →
{declined | closed}`.

### CLI examples

```bash
python3 scripts/mem.py candidates list
python3 scripts/mem.py candidates add --data '{"project_name":"Stirling Residences","address":"Stirling Rd"}'
python3 scripts/mem.py candidates advance-stage --id stirling-residences-2026-05
python3 scripts/mem.py candidates advance-stage --id stirling-residences-2026-05 --stage declined
python3 scripts/mem.py candidates update --id stirling-residences-2026-05 --patch '{"my_max_price_sgd":2150000}'
```

---

## clients/ — agent client files

`clients/index.json` keeps a flat index for `clients list`:

```jsonc
{
  "clients": [
    { "id": "tan-2026-05-01", "name": "Mr Tan", "role": "buyer",
      "status": "qualifying", "updated_at": "2026-05-08T10:30:00Z" }
  ]
}
```

`clients/<id>.json` is the per-client record:

```jsonc
{
  "id": "tan-2026-05-01",
  "name": "Mr Tan",
  "role": "buyer | seller | both",
  "status": "qualifying | viewing | offer | closed | dropped",
  "profile": { /* same shape as profile.json */ },
  "holdings": { "properties": [ /* same shape */ ] },
  "candidates": { "candidates": [ /* same shape */ ] },
  "viewings": [{ "date": "...", "project": "...", "outcome": "..." }],
  "notes": "free text"
}
```

### CLI examples

```bash
python3 scripts/mem.py clients list
python3 scripts/mem.py clients create --data '{"id":"tan-2026-05-01","name":"Mr Tan","role":"buyer"}'
python3 scripts/mem.py clients get --id tan-2026-05-01
python3 scripts/mem.py clients update --id tan-2026-05-01 --patch '{"status":"viewing"}'

# Per-client holdings / candidates: pass --client.
python3 scripts/mem.py holdings list --client tan-2026-05-01
python3 scripts/mem.py candidates add --client tan-2026-05-01 --data '{"project_name":"..."}'
```

---

## Notes

`mem.py notes append` is the convenient way to drop free-text observations
into any record:

```bash
python3 scripts/mem.py notes append --target profile --text "wants ground-floor unit"
python3 scripts/mem.py notes append --target holdings --id my-marine-blue --text "tenant gives notice end Aug"
python3 scripts/mem.py notes append --target candidates --id <cid> --text "viewed; western sun is a deal-breaker"
python3 scripts/mem.py notes append --target clients --client tan-2026-05-01 --text "prefers freehold"
```

## Error contract

| exit code | meaning |
|-----------|---------|
| 0 | success; stdout is JSON; stderr may contain `{"warning":...}` for unknown fields |
| 2 | input error; stderr is `{"error":"...","field":"..."}` (field may be omitted) |
