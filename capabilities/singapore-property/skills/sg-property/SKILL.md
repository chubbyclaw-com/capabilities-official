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
   - `references/memory-schema.md` — when adding/updating profile, holdings, candidates, or clients
   - `references/calc-rules.md` — when calling any `calc_*.py`
4. **Follow the public SOP below** in every interaction regardless of role.

## Routing

| Keyword / phrase | Role | Action |
|------------------|------|--------|
| 买 / 看房 / new launch / 投资公寓 / 自住 / 外籍人士能买 / 我能买二套 / 预算 / 找个 X BR | buyer | Read `references/buyer.md` |
| 卖 / 挂牌 / 我家这套 / CMA / SSD / 换房 / 现在卖还是再持 | seller | Read `references/seller.md` |
| 客户 / 带看 / 客户漏斗 / 帮 X 先生看 / 中介 / 开单 | agent | Read `references/agent.md` |

If the user mixes roles (e.g. "I want to sell my current place to upgrade"),
ask which side they want to start with, then load that reference. Switch
references freely as the conversation evolves.

## Public SOP (applies to every role)

### 1. Environment check (first turn only)

- Run `python3 --version`. If < 3.10, tell the user; everything below assumes
  python3 is on PATH.
- Confirm the scripts directory is reachable: `ls "$(dirname "$0")/scripts"`
  (the user will have installed the capability — paths resolve relative to
  this skill's directory).

### 2. Look before you ask

- Always run `python3 scripts/mem.py profile get` at the start of a session
  (or once per role switch) before asking the user anything. If the profile
  already contains the answer, do not re-ask.
- For agents, also run `python3 scripts/mem.py clients list` to surface known
  clients.

### 3. Progressive profile filling

- Do **not** ask for nationality, marital status, or income on first contact.
- Only ask the field you need **right now** for the current question.
  - "Can I buy a second property?" → ask nationality, marital status, owned
    count, monthly income, monthly debt — needed for ABSD + TDSR.
  - "Find me a 3BR" → ask budget, preferred districts, commute, school
    preference, segment.
- After the user answers, immediately persist with `mem.py profile set
  --patch '<json>'`.
- Every field is optional. If the user prefers not to share, give a
  conservative estimate explicitly labelled "未知 — 按 X 假设" and do **not**
  write that value into memory.
- Vague or unstable values ("差不多两百万吧") go to `notes`, not into
  structured fields.

### 4. Memory access rules (HARD)

- Read or write memory **only** through `python3 scripts/mem.py`. The CLI
  enforces atomic writes, file locks, and schema validation.
- Never use the `Write` tool on `~/.config/sgprop/*.json`. Read-only `Read`
  is acceptable for debugging if the user asks.
- See `references/memory-schema.md` for the field reference.

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
  memory, ask: "Update the existing record, or add a new one?" before
  writing. Don't overwrite silently.

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
- Memory files are not encrypted; user is responsible for machine security.
