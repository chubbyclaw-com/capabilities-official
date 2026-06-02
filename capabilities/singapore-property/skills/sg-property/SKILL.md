---
name: sg-property
description: Use when the user discusses buying, selling, or valuing Singapore residential property (private/HDB/EC), or acts as a Singapore property agent managing clients. Triggers on keywords like 买/卖/看房/估值/挂牌/CMA/出价/客户/带看/condo/HDB/new launch/投资公寓/换房/ABSD/BSD/SSD/TDSR/MSR/yield, addresses or districts in Singapore, and questions about eligibility, taxes, or rental returns for Singapore property.
---

# Singapore Property Decision Assistant

Three role-aware workflows: **buyer**, **seller**, **agent**. This file is the
router; role-specific SOPs live under `references/`.

## How to use this skill

1. **Detect the role** from what the user says (see Routing below).
2. **Read the matching reference** for the detailed workflow:
   - `references/buyer.md` — for any "I want to buy / I'm shopping / can I afford / which project"
   - `references/seller.md` — for "I want to sell / what's my place worth / when to list"
   - `references/agent.md` — for agents managing multiple clients (CMA reports, batch matching, viewings)
3. **Read other references on demand:**
   - `references/memory-conventions.md` — whenever you read or write any
     persistent state via `MemoryWrite / MemoryGet / MemorySearch /
MemoryList / MemoryUpdate / MemoryDelete`
   - `references/calc-rules.md` — when calling any `calc_*.py`
4. **Follow the public SOP below** in every interaction regardless of role.

## Routing

| Keyword / phrase                                                                                                 | Role   | Action                      |
| ---------------------------------------------------------------------------------------------------------------- | ------ | --------------------------- |
| 买 / 看房 / new launch / 投资公寓 / 自住 / 外籍人士能买 / 我能买二套 / 预算 / 找个 X BR                          | buyer  | Read `references/buyer.md`  |
| 卖 / 挂牌 / 我家这套 / CMA / SSD / 换房 / 现在卖还是再持                                                         | seller | Read `references/seller.md` |
| 客户 / 带看 / 客户漏斗 / 帮 X 先生看 / 中介 / 开单 / client / my client / got a client / for a client / 帮客户找 | agent  | Read `references/agent.md`  |

If the user mixes roles (e.g. "I want to sell my current place to upgrade"),
ask which side they want to start with, then load that reference. Switch
references freely as the conversation evolves.

## Public SOP (applies to every role)

### 1. Environment check (lazy)

- Tax / loan / yield numbers come from `scripts/calc_*.py`. The first time
  you need to call one in a session, confirm `python3 --version` is ≥ 3.10
  and the script is reachable; surface a clear error to the user if not.
- Memory is platform-native (`MemoryWrite / MemoryGet / MemorySearch /
MemoryList / MemoryUpdate / MemoryDelete`) — no environment check needed.

### 2. Look before you ask

- At the start of a session (or once per role switch), call
  `MemorySearch("sgprop:profile")` before asking the user anything. If a
  hit comes back, `MemoryGet` it and use the stored fields; do not re-ask.
- For agents, also call `MemorySearch("sgprop:client")` to surface known
  clients.

### 3. Progressive profile filling

- Do **not** ask for nationality, marital status, or income on first contact.
- Only ask the field you need **right now** for the current question.
  - "Can I buy a second property?" → ask nationality, marital status, owned
    count, monthly income, monthly debt — needed for ABSD + TDSR.
  - "Find me a 3BR" → ask budget, preferred districts, commute, school
    preference, segment.
- For structured fields (nationality, residency status, marital status, segment,
  district, HDB/private ownership), use `AskUserQuestion` tool with
  multiple-choice options — do **not** ask these as free-form text.
- After the user answers, persist immediately by **updating** the profile
  memory in place: `MemorySearch("sgprop:profile")` → `MemoryGet(id)` →
  merge the new fields → `MemoryUpdate(id, <new envelope>)` (omit `tags` —
  the identifier is unchanged). If no profile exists yet, just
  `MemoryWrite(..., tags=["sgprop:profile"])`. See
  `references/memory-conventions.md` for the envelope shape, the per-kind
  `tags`, and the full update protocol.
- Every field is optional. If the user prefers not to share, give a
  conservative estimate explicitly labelled "未知 — 按 X 假设" and do **not**
  write that value into memory.
- Vague or unstable values ("差不多两百万吧") go to the `notes` field of the
  parent record (or a separate `sgprop:note`), not into structured fields.

### 3a. Capture clients proactively (agent — HARD)

- When the user acts as an agent and **mentions a client** — even in
  passing, even **without** an explicit "remember / keep track / 记一下 /
  帮我存" (e.g. "got a client wants Tampines 1.5m", "帮一个客户看看 D15 的
  3BR", "my client is selling his HDB") — treat it as **client onboarding**,
  not a throwaway query.
- Persist the client **before or alongside** any search: write/update a
  `sgprop:client` record, and capture the stated requirement as a
  `sgprop:client-candidate` (buyer) or `sgprop:client-holding` (seller), or
  into `profile.preferences`. Follow `references/agent.md` §1. Do **not**
  wait for the user to ask you to save.
- First `MemorySearch("sgprop:client")` to avoid duplicating an existing
  client (match by name / area / requirement); update rather than re-add.
- If the client's name is not given yet, mint a placeholder `client_id`
  (e.g. `client-<area>-YYYY-MM-DD`) and onboard now; ask for the name once
  you've shown first results, then rename via the update protocol.
- This only applies to the agent role. For buyer/seller (the user's own
  search), keep following §3 and §3b — persist the user's own
  `sgprop:profile` (and a `sgprop:holding` per owned property), not a
  client record.
- **Requirement changes are captures too (HARD).** When a known client
  revises a stated requirement mid-conversation — budget, bedrooms,
  location, tenure, segment, timeline — treat it exactly like the initial
  capture: **before or alongside** re-searching, write the new value back
  to that client's `sgprop:client-candidate` (or `profile.preferences`)
  in place via the memory update protocol (Search → Get → merge →
  `MemoryUpdate(id)`). Otherwise the next recall returns the stale
  requirement.
- **An artifact / group file is NOT a substitute for updating memory
  (HARD).** A comparison table, shortlist doc, or CMA you save as a group
  file (`create_artifact`) is a _deliverable snapshot_; the
  `sgprop:client*` memory record is the CRM source of truth that later
  `MemorySearch` reads. They are different stores. When the user says
  "save this to <client>'s file / 存进 X 的档案", **update the client
  memory record first**, then optionally also create the artifact if they
  want a shareable document — never do only the artifact and leave the
  client's memory stale.

### 3b. Capture the user's own situation proactively (buyer / seller — HARD)

- When the user (acting for themselves, not as an agent) states their own
  situation — income, cash / CPF, the properties they **own**, an upgrade /
  sell plan — **or** asks you to "remember my situation / 记住我的情况 /
  帮我存一下", persist it as the canonical envelope records **before or
  alongside** any further analysis. Do **not** wait to be asked, and do
  **not** write a single free-form summary memory.
- **Decompose, never lump.** One logical entity = one record:
  - identity / finance / ownership / intent / preferences → one
    `sgprop:profile`, `tags=["sgprop:profile"]` (create with `MemoryWrite`
    if none, else update in place per §3).
  - **each property the user owns** → its own `sgprop:holding` record,
    `tags=["sgprop:holding", "<address>"]`. An upgrader typically has ≥ 2
    (the home being sold **plus** any investment unit). Always capture each
    holding's `purchase_date` — SSD tiering depends on it.
  - a multi-step plan (e.g. sell-first / buy-first sequencing, an SSD-cliff
    wait) goes in the profile's `notes` or a `sgprop:note`, **not** into tags.
- **Never substitute ad-hoc descriptive tags** (`"property-portfolio"`,
  `"upgrade-plan"`, `"absd"`, `"ssd"`) for the canonical `sgprop:*` atoms.
  The retrieval SOP (§2) searches `sgprop:profile` / `sgprop:holding`; a
  freestyle-tagged record will not be found and the next session re-asks
  everything. Follow `references/seller.md` §1 and
  `references/memory-conventions.md`.

### 4. Memory access rules (HARD)

- Read or write persistent state **only** through the platform
  `Memory*` tools. Do **not** invent local file storage (`~/.config/...`,
  `Write` to disk, etc.) for any sgprop data.
- Every `MemoryWrite` must (a) lead its `value` with the
  `sgprop:<kind> | <identifier>` header line (human-readable + JSON-parse
  anchor) **and** (b) pass `tags=["sgprop:<kind>", "<identifier>", ...]` —
  the stable, verbatim retrieval atoms that make `MemorySearch("sgprop:...")`
  hit. Retrieval rides on `tags`, not on MetaGen's keywords. See
  `references/memory-conventions.md` for the per-kind `tags` table and
  templates.
- Default to `scope=user` (rely on the platform default; do not pass
  `scope` unless overriding). Only use `scope=chatgroup` when the user is
  in a group chat **and** explicitly asks to share, **and** has been warned
  that only the group owner can write and all members can read.
- Sensitive fields (income, CPF balance, NRIC / nationality) write to
  `scope=user` only. Confirm with the user before persisting if the
  conversation context is a group chat.
- To edit a stored record, use `MemoryUpdate(id, value)` in place via the
  Search → Get → merge → `MemoryUpdate(id)` protocol — do **not** write a new
  record and delete the old. Omit `tags` so the existing retrieval atoms are
  kept; pass a new `tags` array only when the identifier itself changes (a
  renamed client, a re-addressed holding). Write independent event records
  (`sgprop:viewing`, `sgprop:offer`, `sgprop:note`) for new occurrences, and
  `MemoryDelete(id)` to remove. See `references/memory-conventions.md`.

### 5. Policy math rules (HARD)

- Never compute ABSD, BSD, SSD, TDSR, MSR, yield, holding cost, or breakeven
  by hand. Always shell out to the matching `calc_*.py` script with stdin
  JSON.
- Surface the script's `breakdown` field to the user — they want to see how
  the number was reached.
- See `references/calc-rules.md` for input shapes and policy versions.

### 6. MCP error handling

- The skill calls the `sgprop` MCP for data (`sgprop_search_projects`,
  `sgprop_project_report`, `sgprop_transactions`, `sgprop_supply_outlook`,
  `sgprop_location_context`).
- If a tool returns an error (network, auth, upstream), tell the user the
  raw reason and suggest a retry or auth check. Do **not** invent data or
  paper over the failure.

### 7. Conflicting values

- If the user gives a new value that contradicts something already in
  memory, follow the conflict protocol in `references/memory-conventions.md`:
  Search → Get, restate the diff to the user, ask "覆盖 / 追加新条 / 保留
  旧值", then apply the answer. Never overwrite silently.

### 8. Currency, units, dates

- All money in SGD unless the user specifies otherwise.
- Floor area in `sqft`. Distance in `km` for facilities, `min` for transit
  walking time.
- Dates in ISO `YYYY-MM-DD` (or `YYYY-MM` where the day is unknown).

### 9. Search result display (HARD)

Applies whenever `sgprop_search_projects`, `sgprop_supply_outlook`, or
`sgprop_project_report` returns data that includes nearby or listed
projects — regardless of role (buyer, seller, agent), and including
school-catchment filtered calls and single-candidate deep-dive calls.

**Standard layout (all roles except agent batch-matching):**

1. **Upcoming / new launch first** — any project with `status` of
   `upcoming`, `new_launch`, or `preview` must appear in its own
   clearly-labelled section at the top of the reply (use the heading
   "即将推出 / New launches nearby"). Never merge these into a combined
   table with completed or resale projects. This applies even when only
   one upcoming project is found.
2. **Completed / resale second** — separate section below. Statuses
   `completed`, `resale`, `sold_out`, `TOP_issued` belong here. For
   any ambiguous status (e.g. `under_construction`, `TOP_pending`),
   place in this section and note the status parenthetically.
3. **Explicitly state when none found** — if no projects with an
   upcoming status are in the results, write "附近暂无即将推出的新项目"
   (or English equivalent). Do not stay silent.

**Aggregate supply data** — if `sgprop_supply_outlook` returns totals
or counts rather than per-project records with `status` fields, name
any specific upcoming projects mentioned in the narrative and apply the
section heading to them. If none are named, state so explicitly.

**Agent batch-matching matrix exception** — when producing the
clients × projects matrix (agent.md §4), sort matrix rows so
upcoming/new_launch/preview projects appear at the top of the matrix
before completed projects. Row-ordering substitutes for the
separate-section requirement in this format.

Rationale: upcoming projects are the highest-value signal across all
three workflows — the buy-side opportunity the user doesn't yet know
about, the new supply pressure a seller must price around, the launch
inventory an agent needs to brief clients on. Burying them in a flat
list is a material omission.

## Typical opening lines

- Buyer: "外籍人士在新加坡能买什么", "我看上 D15 一个 3BR 想出价",
  "150 万预算自住怎么挑", "Can I afford a second condo?"
- Seller: "我这套该卖多少钱", "现在卖还是再持一年", "夫妻一起换房怎么操作"
- Agent: "给 Tan 先生做个 CMA", "我现在手上 5 个客户，预算 200-300 万自住",
  "近期 D15 哪些项目值得带看"

## Limits (v1)

- HDB BTO/SBF tool is a placeholder in the underlying MCP — for resale HDB
  use `sgprop_search_projects --segment hdb_resale`.
- No automatic bidding / signing. Decision support only.
- No commercial / industrial / overseas property.
