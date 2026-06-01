# Memory conventions

All `sgprop` persistent state lives in the ChubbyClaw platform memory store,
accessed via the native `MemoryWrite / MemoryGet / MemorySearch / MemoryList /
MemoryUpdate / MemoryDelete` tools. There is **no** local `~/.config/sgprop`
directory and no `mem.py` CLI any more — those were removed when we moved to
the platform memory tool.

Platform contract (excerpt of `chubbyclaw/docs/design/14-memory-system.md`):

| Item | Value |
|------|-------|
| Tools | `MemoryWrite(value, scope?, expires_in_days?)`, `MemoryGet(id)`, `MemorySearch(query, limit?)`, `MemoryList(limit?)`, `MemoryUpdate(id, value)`, `MemoryDelete(id)` |
| `scope` | `user` (default) or `chatgroup` — server-injected `subject_type / subject_id / actor` cannot be set by the model |
| `value` | Plaintext ≤ 8 KB; encrypted at rest with a per-subject DEK |
| Metadata | Server LLM generates `summary` (≤ 200 chars) + `keywords` (≤ 8 items) at write/update time. `MemorySearch` returns meta only; call `MemoryGet(id)` to read `value` |
| Editing | `MemoryUpdate(id, value)` replaces an existing record's content **in place**, keeping the same `id` and re-deriving summary/keywords. This is the correct way to apply a correction — not write-new-then-delete |

Skill responsibility:

1. Format `value` so MetaGen produces useful summary + keywords.
2. When an existing record's fields change, edit it **in place** with the
   Search → Get → merge → `MemoryUpdate(id)` protocol — do **not** write a new
   record and delete the old one (see [Update protocol](#update-protocol)).
3. Keep all sgprop writes under `scope=user` unless the user is in a group
   chat and explicitly asks to share — see [Scope](#scope) below.

## Record envelope

Every memory record is one logical entity. The `value` text follows this
shape:

```
sgprop:<kind> | <stable-id-or-name>

key1: value1
key2: value2
...

```json
{ ...full structured payload... }
```
```

- The **first line** is the discoverability header. `sgprop`, `<kind>`, and
  the identifier nearly always end up in the MetaGen `keywords`. Without
  this line, future `MemorySearch` calls cannot find the record.
- The **plaintext key:value block** carries the most important facts so the
  MetaGen `summary` reads naturally.
- The **fenced JSON** is the machine-readable canonical form. After
  `MemoryGet(id)`, parse this block to get every field.
- Always echo the entity's key identifier(s) — `client_id`, full address,
  project name — verbatim in the header. MetaGen will not invent keywords
  that are absent from the body.

## Record kinds

| Kind | Used by | Identifier echoed in header | Count |
|------|---------|------------------------------|-------|
| `sgprop:profile` | buyer / seller | (none — one per user) | 1 |
| `sgprop:holding` | seller | full `address` | N |
| `sgprop:candidate` | buyer | `project_name` + capture month | N |
| `sgprop:client` | agent | `client_id` slug `<surname>-YYYY-MM-DD` | N |
| `sgprop:client-holding` | agent | `client_id` + `address` | N |
| `sgprop:client-candidate` | agent | `client_id` + `project_name` | N |
| `sgprop:viewing` | seller / agent | parent `address` or `project_name` + date | N |
| `sgprop:offer` | seller / agent | parent `address` or `project_name` + date | N |
| `sgprop:note` | any | parent record identifier (free text) | N |

Each record is independent. `client` is split from `client-holding /
client-candidate` so that updating one client's candidate list does not
need to rewrite a packed payload, and so a single record always stays well
under the 8 KB cap.

### Templates

#### `sgprop:profile`

```
sgprop:profile

nationality: SC
marital_status: married
spouse_nationality: SC
household_size: 3
monthly_income_sgd: 18000
monthly_debt_sgd: 2500
cpf_oa_sgd: 180000
cash_available_sgd: 250000
private_count: 0
hdb_count: 1
budget_max_sgd: 2500000
bedrooms: [3, 4]
districts_prefer: [15, 16]
intent: upgrade

```json
{
  "identity": { "nationality": "SC", "marital_status": "married",
                "spouse_nationality": "SC", "household_size": 3,
                "children": [{ "age": 6, "school_pref": "Nanyang Primary" }] },
  "finance": { "monthly_income_sgd": 18000, "monthly_debt_sgd": 2500,
               "cpf_oa_sgd": 180000, "cash_available_sgd": 250000 },
  "ownership": { "private_count": 0, "hdb_count": 1, "owns_overseas": false },
  "preferences": { "budget_max_sgd": 2500000, "bedrooms": [3, 4],
                   "districts_prefer": ["15", "16"], "districts_avoid": ["22"],
                   "segment": ["resale", "new_launch"], "tenure_pref": "freehold",
                   "must_haves": ["near MRT 10min", "1km top primary school"],
                   "work_location": "Raffles Place" },
  "intent": "upgrade",
  "notes": ""
}
```
```

#### `sgprop:holding`

```
sgprop:holding | Marine Blue #18-05

type: private
purchase_date: 2019-08
purchase_price_sgd: 1380000
current_loan_sgd: 720000
remaining_lease_years: 86
intent: sell

```json
{ "address": "Marine Blue #18-05", "type": "private",
  "purchase_date": "2019-08", "purchase_price_sgd": 1380000,
  "current_loan_sgd": 720000, "remaining_lease_years": 86,
  "renovated_year": 2020, "intent": "sell",
  "sales": { "listing_price_sgd": 1880000, "listed_date": "2026-05-09",
             "status": "live" },
  "notes": "" }
```
```

> `sales.viewings` and `sales.offers` are **not** packed here. Use the
> independent `sgprop:viewing` / `sgprop:offer` records below.

#### `sgprop:candidate`

```
sgprop:candidate | Stirling Residences | 2026-05

address: Stirling Rd
stage: viewed
asking_price_sgd: 2350000
my_max_price_sgd: 2200000
estimated_value_sgd: 2280000

```json
{ "project_name": "Stirling Residences", "address": "Stirling Rd",
  "stage": "viewed", "viewed_dates": ["2026-05-10"],
  "unit_details": { "stack": "05", "floor": 18, "size_sqft": 980, "bedrooms": 3 },
  "asking_price_sgd": 2350000, "my_max_price_sgd": 2200000,
  "estimated_value_sgd": 2280000,
  "pros": ["1km Henry Park Pri", "Queenstown MRT 7min"],
  "cons": ["west sun"], "notes": "" }
```
```

Stage progresses: `shortlist → viewing_scheduled → viewed → offered →
{declined | closed}`.

#### `sgprop:client`

```
sgprop:client | tan-2026-05-08 | Mr Tan

role: buyer
status: qualifying

```json
{ "client_id": "tan-2026-05-08", "name": "Mr Tan", "role": "buyer",
  "status": "qualifying",
  "profile": { /* same shape as sgprop:profile JSON */ },
  "notes": "" }
```
```

`client_id` is `<surname>-YYYY-MM-DD`, slug-safe. Status progresses:
`qualifying → viewing → offer → closed`, or `qualifying → dropped`.

#### `sgprop:client-holding`

```
sgprop:client-holding | tan-2026-05-08 | Block 123 Tampines St 11 #08-12

type: hdb
purchase_date: 2015-04
purchase_price_sgd: 480000

```json
{ "client_id": "tan-2026-05-08", "address": "Block 123 Tampines St 11 #08-12",
  "type": "hdb", "purchase_date": "2015-04", "purchase_price_sgd": 480000,
  "intent": "sell", "notes": "" }
```
```

#### `sgprop:client-candidate`

```
sgprop:client-candidate | tan-2026-05-08 | Bedok South Residences

stage: shortlist

```json
{ "client_id": "tan-2026-05-08", "project_name": "Bedok South Residences",
  "stage": "shortlist", "asking_price_sgd": 1850000, "notes": "" }
```
```

#### `sgprop:viewing`

```
sgprop:viewing | Marine Blue #18-05 | 2026-05-12

outcome: interested
attendees: 2

```json
{ "parent_kind": "holding", "parent_id": "Marine Blue #18-05",
  "date": "2026-05-12", "outcome": "interested", "attendees": 2,
  "notes": "couple, second viewing" }
```
```

For an agent client's viewing, set `parent_kind: "client-candidate"` and
`parent_id: "<client_id> | <project_name>"`.

#### `sgprop:offer`

```
sgprop:offer | Marine Blue #18-05 | 2026-05-15

amount_sgd: 1830000
status: rejected

```json
{ "parent_kind": "holding", "parent_id": "Marine Blue #18-05",
  "date": "2026-05-15", "amount_sgd": 1830000, "status": "rejected",
  "notes": "buyer pushed back; we held at 1.88m" }
```
```

#### `sgprop:note`

```
sgprop:note | candidate | Stirling Residences

text: viewed 2026-05-10; agent quoted 2.32m floor

```json
{ "parent_kind": "candidate", "parent_id": "Stirling Residences",
  "text": "viewed 2026-05-10; agent quoted 2.32m floor",
  "date": "2026-05-10" }
```
```

## Update protocol

**When a field on an existing record changes, edit that record in place with
`MemoryUpdate(id, value)`.** This is the right tool whenever the new value
*replaces* an old one on a record you can locate by `id`: a corrected budget,
an advanced `stage`, a renamed client, a revised `status`. `MemoryUpdate`
keeps the same `id`, re-derives the summary/keywords, and leaves no stale
duplicate behind.

To edit a record:

1. `MemorySearch("sgprop:<kind> <identifier>")` to locate the existing
   memory's `id`.
2. `MemoryGet(id)` to read the current canonical JSON.
3. Merge the new fields into the JSON in your head / scratchpad to build the
   complete new envelope (`MemoryUpdate` replaces the whole `value`, so it
   must carry every field, not just the changed one).
4. `MemoryUpdate(id, <new envelope>)` — overwrites the record in place.

Do **not** `MemoryWrite` a second record and then `MemoryDelete` the old one
to simulate an edit — that briefly leaves two conflicting copies and is the
exact pattern `MemoryUpdate` exists to replace. Only write-then-delete when
the user explicitly wants the old value preserved as a separate history entry
(see [Conflicts](#conflict-handling)).

### When NOT to use MemoryUpdate

- **A brand-new entity** (a client you have not stored yet, a first profile):
  there is no `id` to update → `MemoryWrite`.
- **Appending an event** (the user did something new — a viewing, an offer, a
  note): write a brand-new `sgprop:viewing` / `sgprop:offer` / `sgprop:note`
  record; do **not** mutate the parent `holding` / `candidate` and do **not**
  `MemoryUpdate` the parent. Recall via `MemorySearch("sgprop:viewing
  <address>")`.
- **Removing** a record: `MemoryDelete(id)`.

So: a stored field *changed* → `MemoryUpdate`. Something *new happened* →
`MemoryWrite` a new record. A record is *gone* → `MemoryDelete`.

### Cascading delete

When a parent entity is removed (drop a client, dispose of a holding):

1. `MemorySearch("<parent_identifier>")` — find every related record
   (`client-holding`, `client-candidate`, `viewing`, `offer`, `note`).
2. Read each result's `id`.
3. `MemoryDelete(id)` for every one of them, plus the parent itself.

There is no automatic cascade; the skill drives it.

## Conflict handling

When the user gives a value that contradicts something already stored:

1. `MemorySearch` then `MemoryGet` to surface the current state.
2. Restate the diff to the user: "已记录 budget 2.5m,你刚说 2.2m。"
3. Ask: overwrite / add a new entry / keep the existing? Do **not** silently
   overwrite.
4. Apply the answer with the update protocol.

## Scope

The default for every sgprop write is `scope=user`.

| Scenario | scope |
|----------|-------|
| Buyer / seller workflow (`profile`, `holding`, `candidate`, `viewing`, `offer`, `note`) | `user` |
| Agent managing their own clients (`client`, `client-holding`, `client-candidate`) | `user` (agent-private) |
| Family / friends in a group chat asking to share a candidate shortlist | `chatgroup` (only if the user explicitly requests, and only the group owner can write) |

Implementation notes:

- Pass `scope=user` only when the platform's default has been overridden in
  the current conversation; otherwise omit the field and rely on the
  default.
- Before writing `scope=chatgroup`, warn the user: "群级共享记忆只有群主能
  写,而且任何群成员都能读 — 确定要把这条放到群里吗?"
- If the user is not in a group context, refuse a `chatgroup` write.

## Expiry

Use `expires_in_days` when the record has a clear shelf-life. Examples:

| Record | Suggested `expires_in_days` |
|--------|------------------------------|
| SSD watch window for a holding bought < 3 years ago | days remaining to the 3-year mark + 30 |
| `sgprop:viewing` follow-up reminder | 14 |
| `sgprop:candidate` flagged "watch only" | 90 |
| `sgprop:offer` historical | none (long-lived) |

Long-lived facts (profile, client header, holding header) omit
`expires_in_days`.

## Quick reference — what to call when

| User says | Call |
|-----------|------|
| "我是谁的画像" / first-time entry | `MemorySearch("sgprop:profile")` → `MemoryGet(id)` (or write a new one if empty) |
| "我新看了一套" | `MemoryWrite("sgprop:candidate \| <project> \| <month>", ...)` |
| "我去看过 Stirling 了" | `MemoryWrite("sgprop:viewing \| Stirling Residences \| <date>", ...)` |
| "我的预算上调到 2.7m" | Search profile → Get → merge `budget_max_sgd` → `MemoryUpdate(id)` |
| "把 Tan 的状态改成 offer" | Search `sgprop:client tan-2026-05-08` → Get → merge `status` → `MemoryUpdate(id)` |
| "列一下我手上的客户" | `MemorySearch("sgprop:client")` |
| "删掉 Tan 这个客户" | Search `tan-2026-05-08` → delete all hits |
| "记一笔:这套西晒" | `MemoryWrite("sgprop:note \| candidate \| <project>", ...)` |
