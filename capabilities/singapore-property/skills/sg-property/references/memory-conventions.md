# Memory conventions

All `sgprop` persistent state lives in the ChubbyClaw platform memory store,
accessed via the native `write_memory / get_memory / search_memory / list_memories /
update_memory / delete_memory` tools. There is **no** local `~/.config/sgprop`
directory and no `mem.py` CLI any more — those were removed when we moved to
the platform memory tool.

Platform contract (excerpt of `chubbyclaw/docs/design/14-memory-system.md`):

| Item | Value |
|------|-------|
| Tools | `write_memory(value, tags?, scope?, expires_in_days?)`, `get_memory(id)`, `search_memory(query, limit?)`, `list_memories(limit?)`, `update_memory(id, value, tags?)`, `delete_memory(id)` |
| `scope` | `user` (default) or `chatgroup` — server-injected `subject_type / subject_id / actor` cannot be set by the model |
| `value` | Plaintext ≤ 8 KB; encrypted at rest with a per-subject DEK |
| Metadata | Server LLM (MetaGen) generates `summary` (≤ 200 chars) + natural-language `keywords` (≤ 8 items) at write/update time. `search_memory` returns meta only; call `get_memory(id)` to read `value` |
| `tags` | Optional `string[]` the **caller** passes to `write_memory` / `update_memory`: explicit, stable retrieval atoms stored **verbatim**. They sit alongside the LLM `keywords` and both participate in `search_memory` substring matching, but `tags` are **never** rewritten or dropped by MetaGen — this is what makes the `sgprop:<kind>` atoms reliably findable. On `update_memory`: **omit** `tags` = keep the record's existing tags (the norm when you only change `value`); **pass** `tags` = full overwrite (pass `[]` to clear) |
| Editing | `update_memory(id, value)` replaces an existing record's content **in place**, keeping the same `id` and re-deriving summary/keywords (existing `tags` are preserved unless you pass new ones). This is the correct way to apply a correction — not write-new-then-delete |

Skill responsibility:

1. Format `value` so MetaGen produces a useful summary, and pass the
   record's stable retrieval atoms via `tags` (see [Record envelope](#record-envelope)).
2. When an existing record's fields change, edit it **in place** with the
   Search → Get → merge → `update_memory(id)` protocol — do **not** write a new
   record and delete the old one (see [Update protocol](#update-protocol)).
3. Keep all sgprop writes under `scope=user` unless the user is in a group
   chat and explicitly asks to share — see [Scope](#scope) below.

## Record envelope

Every memory record is one logical entity. Each `write_memory` carries two
things: the `value` text (below) **and** a `tags` array of the record's
stable retrieval atoms. The `value` follows this shape:

```
sgprop:<kind> | <stable-id-or-name>

key1: value1
key2: value2
...

```json
{ ...full structured payload... }
```
```

Pass the matching `tags` on every write — `sgprop:<kind>` plus that kind's
identifier(s):

```
write_memory(value="""sgprop:candidate | Stirling Residences | 2026-05
...
""", tags=["sgprop:candidate", "Stirling Residences"])
```

- **Retrieval is carried by `tags`, not by MetaGen.** The atoms you pass in
  `tags` are stored verbatim and matched by `search_memory` as-is, so
  `search_memory("sgprop:candidate")` / `search_memory("sgprop:client <id>")`
  reliably hit. (MetaGen's `keywords` are natural-language and may drop the
  `sgprop:<kind>` header — never rely on them for atom lookup.)
- The **first line** of `value` is still the human-readable header and the
  anchor for JSON parsing, but it no longer carries the retrieval job; keep
  it in sync with the `tags` (same `sgprop:<kind>` + identifiers).
- The **plaintext key:value block** carries the most important facts so the
  MetaGen `summary` reads naturally.
- The **fenced JSON** is the machine-readable canonical form. After
  `get_memory(id)`, parse this block to get every field.
- Always echo the entity's key identifier(s) — `client_id`, full address,
  project name — verbatim in **both** the header and `tags`.

## Record kinds

| Kind | Used by | Identifier echoed in header | `tags` to pass | Count |
|------|---------|------------------------------|----------------|-------|
| `sgprop:profile` | buyer / seller | (none — one per user) | `["sgprop:profile"]` | 1 |
| `sgprop:holding` | seller | full `address` | `["sgprop:holding", "<address>"]` | N |
| `sgprop:candidate` | buyer | `project_name` + capture month | `["sgprop:candidate", "<project_name>"]` | N |
| `sgprop:client` | agent | `client_id` slug `<surname>-YYYY-MM-DD` | `["sgprop:client", "<client_id>"]` | N |
| `sgprop:client-holding` | agent | `client_id` + `address` | `["sgprop:client-holding", "<client_id>", "<address>"]` | N |
| `sgprop:client-candidate` | agent | `client_id` + `project_name` | `["sgprop:client-candidate", "<client_id>", "<project_name>"]` | N |
| `sgprop:viewing` | seller / agent | parent `address` or `project_name` + date | `["sgprop:viewing", "<parent identifier>"]` | N |
| `sgprop:offer` | seller / agent | parent `address` or `project_name` + date | `["sgprop:offer", "<parent identifier>"]` | N |
| `sgprop:note` | any | parent record identifier (free text) | `["sgprop:note", "<parent identifier>"]` | N |

The `tags` column is the stable retrieval atom set: always `sgprop:<kind>`
plus the identifier(s) future `search_memory` calls will query on. Pass it
verbatim on every `write_memory`. For `client` records also include the
client name as an extra tag if you want name lookups to hit
(`["sgprop:client", "<client_id>", "<name>"]`).

Each record is independent. `client` is split from `client-holding /
client-candidate` so that updating one client's candidate list does not
need to rewrite a packed payload, and so a single record always stays well
under the 8 KB cap.

### Templates

Each template shows the `value`. The `tags` to pass alongside it are noted
under each block.

#### `sgprop:profile`

`tags=["sgprop:profile"]`

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

`tags=["sgprop:holding", "Marine Blue #18-05"]`

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

`tags=["sgprop:candidate", "Stirling Residences"]`

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

`tags=["sgprop:client", "tan-2026-05-08", "Mr Tan"]`

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

`tags=["sgprop:client-holding", "tan-2026-05-08", "Block 123 Tampines St 11 #08-12"]`

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

`tags=["sgprop:client-candidate", "tan-2026-05-08", "Bedok South Residences"]`

```
sgprop:client-candidate | tan-2026-05-08 | Bedok South Residences

stage: shortlist

```json
{ "client_id": "tan-2026-05-08", "project_name": "Bedok South Residences",
  "stage": "shortlist", "asking_price_sgd": 1850000, "notes": "" }
```
```

#### `sgprop:viewing`

`tags=["sgprop:viewing", "Marine Blue #18-05"]`

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

For an agent client's viewing, set `parent_kind: "client-candidate"`,
`parent_id: "<client_id> | <project_name>"`, and pass
`tags=["sgprop:viewing", "<client_id>", "<project_name>"]`.

#### `sgprop:offer`

`tags=["sgprop:offer", "Marine Blue #18-05"]`

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

`tags=["sgprop:note", "Stirling Residences"]`

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
`update_memory(id, value)`.** This is the right tool whenever the new value
*replaces* an old one on a record you can locate by `id`: a corrected budget,
an advanced `stage`, a renamed client, a revised `status`. `update_memory`
keeps the same `id`, re-derives the summary/keywords, and leaves no stale
duplicate behind.

To edit a record:

1. `search_memory("sgprop:<kind> <identifier>")` to locate the existing
   memory's `id`.
2. `get_memory(id)` to read the current canonical JSON.
3. Merge the new fields into the JSON in your head / scratchpad to build the
   complete new envelope (`update_memory` replaces the whole `value`, so it
   must carry every field, not just the changed one).
4. `update_memory(id, <new envelope>)` — overwrites the record in place.
   **Omit `tags`** so the record keeps its existing retrieval atoms; you are
   only changing `value`, not how the record is found.

**Tags on update — only when the identifier itself changes.** Pass a new
`tags` array to `update_memory` *solely* when the atom you search on moves —
e.g. a client renamed (`client_id` re-slugged) or a holding re-addressed.
Then pass the full replacement set (`update_memory(id, value, tags=["sgprop:client", "<new_id>", "<new name>"]`)
and update the `value` header to match. A field edit that does **not** touch
the identifier (a corrected budget, an advanced `stage`, a revised `status`)
leaves `tags` untouched — omit the parameter.

Do **not** `write_memory` a second record and then `delete_memory` the old one
to simulate an edit — that briefly leaves two conflicting copies and is the
exact pattern `update_memory` exists to replace. Only write-then-delete when
the user explicitly wants the old value preserved as a separate history entry
(see [Conflicts](#conflict-handling)).

### When NOT to use update_memory

- **A brand-new entity** (a client you have not stored yet, a first profile):
  there is no `id` to update → `write_memory`.
- **Appending an event** (the user did something new — a viewing, an offer, a
  note): write a brand-new `sgprop:viewing` / `sgprop:offer` / `sgprop:note`
  record; do **not** mutate the parent `holding` / `candidate` and do **not**
  `update_memory` the parent. Recall via `search_memory("sgprop:viewing
  <address>")`.
- **Removing** a record: `delete_memory(id)`.

So: a stored field *changed* → `update_memory`. Something *new happened* →
`write_memory` a new record. A record is *gone* → `delete_memory`.

### Cascading delete

When a parent entity is removed (drop a client, dispose of a holding):

1. `search_memory("<parent_identifier>")` — find every related record
   (`client-holding`, `client-candidate`, `viewing`, `offer`, `note`).
2. Read each result's `id`.
3. `delete_memory(id)` for every one of them, plus the parent itself.

There is no automatic cascade; the skill drives it.

## Conflict handling

When the user gives a value that contradicts something already stored:

1. `search_memory` then `get_memory` to surface the current state.
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
| "我是谁的画像" / first-time entry | `search_memory("sgprop:profile")` → `get_memory(id)` (or `write_memory(..., tags=["sgprop:profile"])` if empty) |
| "我新看了一套" | `write_memory("sgprop:candidate \| <project> \| <month>", ..., tags=["sgprop:candidate", "<project>"])` |
| "我去看过 Stirling 了" | `write_memory("sgprop:viewing \| Stirling Residences \| <date>", ..., tags=["sgprop:viewing", "Stirling Residences"])` |
| "我的预算上调到 2.7m" | Search profile → Get → merge `budget_max_sgd` → `update_memory(id)` (tags unchanged) |
| "把 Tan 的状态改成 offer" | Search `sgprop:client tan-2026-05-08` → Get → merge `status` → `update_memory(id)` (tags unchanged) |
| "列一下我手上的客户" | `search_memory("sgprop:client")` |
| "删掉 Tan 这个客户" | Search `tan-2026-05-08` → delete all hits |
| "记一笔:这套西晒" | `write_memory("sgprop:note \| candidate \| <project>", ..., tags=["sgprop:note", "<project>"])` |
