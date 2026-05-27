# Agent workflow

Use this reference when the user is a property agent juggling multiple
clients. Many steps reuse the buyer/seller logic, but scoped to a client
record.

## 1. Client onboarding

`MemorySearch("sgprop:client")` — see existing clients.

For a new client, write a `sgprop:client` record:

```
MemoryWrite(value="""sgprop:client | tan-2026-05-08 | Mr Tan

role: buyer
status: qualifying

```json
{"client_id":"tan-2026-05-08","name":"Mr Tan","role":"buyer",
 "status":"qualifying"}
```
""")
```

`client_id` should be slug-safe (lowercase letters, digits, hyphens). A
typical pattern is `<surname>-<YYYY-MM-DD>`. Always echo `client_id` and
name in the header so MetaGen captures them as keywords.

`role` is one of: `buyer`, `seller`, `both`.

## 2. Per-client profile + holdings + candidates

Client-scoped data lives in **separate** memory records — not packed into
the `sgprop:client` header. Use the dedicated kinds:

- `sgprop:client-holding` — a property the client owns
- `sgprop:client-candidate` — a property the client is evaluating

Always echo the `client_id` in the header so future searches by client
work.

```
# Client's existing holding (for upgrade work)
MemoryWrite(value="""sgprop:client-holding | tan-2026-05-08 | Block 123 Tampines St 11 #08-12

type: hdb
purchase_date: 2015-04
purchase_price_sgd: 480000

```json
{"client_id":"tan-2026-05-08",
 "address":"Block 123 Tampines St 11 #08-12","type":"hdb",
 "purchase_date":"2015-04","purchase_price_sgd":480000}
```
""")
```

```
# Client's candidate
MemoryWrite(value="""sgprop:client-candidate | tan-2026-05-08 | Bedok South Residences

stage: shortlist

```json
{"client_id":"tan-2026-05-08","project_name":"Bedok South Residences",
 "stage":"shortlist"}
```
""")
```

Profile fields (income / nationality / preferences) live inside the
`profile` substructure of the `sgprop:client` record. Update them via the
client update protocol: `MemorySearch("sgprop:client tan-2026-05-08")` →
`MemoryGet(id)` → merge `profile.<field>` into JSON → `MemoryWrite`
new envelope → `MemoryDelete(old id)`.

To list everything for a client:

- `MemorySearch("tan-2026-05-08")` returns the client header plus every
  `client-holding` / `client-candidate` / `viewing` / `offer` / `note`
  that mentions the client_id (MetaGen will have indexed those records).
  Then `MemoryGet(id)` the ones you need.

## 3. Client requirement gathering

- For buyer clients, work through the buyer workflow
  (`references/buyer.md`), but **swap each record kind for its
  client-scoped equivalent**:
  - `sgprop:profile` (in the user workflow) → `profile` field inside the
    `sgprop:client` record
  - `sgprop:candidate` → `sgprop:client-candidate` (with `client_id`)
  - `sgprop:viewing` / `sgprop:offer` / `sgprop:note` → still as
    independent records, but set `parent_kind: "client-candidate"` and
    write `<client_id> | <project>` in the header
- For seller clients, work through the seller workflow
  (`references/seller.md`) with the same swap:
  - `sgprop:holding` → `sgprop:client-holding`
- For `role: both`, sequence: settle the sell side first (cash + ABSD
  refund timing), then the buy side.

## 4. Batch matching

When the agent says "5 clients, $2-3m, family upgrade":

1. `MemorySearch("sgprop:client")` to find clients.
2. For each, `MemoryGet(id)` to read their `profile.preferences` from the
   client JSON body.
3. Run a single `sgprop_search_projects` with the union of constraints.
4. Score each project against each client (district match, school match,
   price band).
5. Output a matrix: clients × top 5 projects with green/yellow/red
   indicators. Sort matrix rows so upcoming/new_launch/preview projects
   appear first — see SKILL.md SOP §9 (batch-matching matrix exception).

## 5. CMA report generation

For seller clients the agent will need a CMA they can hand to their
client. Format:

```markdown
# CMA — Marine Blue #18-05
Generated: 2026-05-08
Agent: <agent name>

## Subject unit
| Detail | Value |
|--------|-------|
| Address | Marine Blue #18-05 |
| Size | 980 sqft, 3BR |
| Tenure | 99 yrs from 2014 (87 left) |
| Last reno | 2020 |

## Comparable sales (last 12 months, same project)
| Date | Floor | Size | PSF | Price |
|------|-------|------|-----|-------|
| ... |

## Comparable sales (nearby projects)
| ... |

## Recommended pricing
| Tier | Price | PSF | Justification |
|------|-------|-----|---------------|
| Aggressive | $1.95m | $1,990 | top 10% of recent comparables |
| Market | $1.88m | $1,918 | median |
| Quick | $1.82m | $1,857 | -3% under median for 30-day sale |

## Costs to seller (estimated)
| Item | Amount |
|------|--------|
| SSD | $0 (held > 3 years) |
| Agent fee 2% | $37,600 |
| Lawyer | $2,800 |
| Loan settlement | $720,000 |
| Net to seller (at market) | $1,119,600 |
```

Pull data via `sgprop_project_report` + `sgprop_transactions`. Compute
SSD with `calc_ssd.py`. Sale-cost numbers come from the seller workflow.

Save the rendered Markdown to a file the user can attach in email — ask
where they want it saved.

## 6. Multi-client viewing route

When the agent has 3-5 viewings in a half-day:

1. Pull each candidate's address.
2. Suggest the order based on geographic clustering (manual eyeballing or
   the `singapore-onemap` capability if installed).
3. Add ~30 min per viewing + travel time.
4. Output a printable schedule (start time per stop).

If `singapore-onemap` is available, you can use its routing tool to get
travel times. Otherwise just present the order and ask the agent to
verify.

## 7. Funnel tracking

Status progression for a client:

`qualifying → viewing → offer → closed`
`qualifying → dropped` (cold-cancelled)

Update `status` with the client update protocol: Search → Get → merge
`status` → Write → Delete old.

A weekly funnel report:

- `MemorySearch("sgprop:client")` (raise `limit` if you have many clients).
- `MemoryGet(id)` each to read `status` and the platform record's
  `updated_at`.
- Group by status, count, and surface stale ones (`updated_at` not changed
  in > 14 days — chase up).

## 8. New launch tracking

Agents working a new launch want to monitor take-up:

```
sgprop_search_projects --status new_launch --district <d>
sgprop_project_report --project "<name>" --sections new_launch_progress,transactions
```

Apply SKILL.md SOP §9 display rule when presenting results — upcoming
projects must be in a dedicated top section.

Compare take-up rate to peers; surface to the agent for client
discussions ("project A is 80% sold in 4 months, project B is 30% in 8
months").

## 9. En bloc candidate hunting

Filter old + freehold projects with under-utilised GFA:

```
sgprop_search_projects --segment private --tenure freehold \
  --top_year_to 2000
```

Then per candidate:
```
sgprop_project_report --project "..." --sections meta,tenure
sgprop_location_context --address "..." (master_plan section)
```

Score by (current GFA / max GFA) and project age. Output a list for the
agent to pitch to clients.

## Tips

- Always store the agent's own profile (commission rates, agency contact)
  in a `sgprop:profile` record — saves them retyping.
- Use `sgprop:note` records (one per observation, with
  `parent_kind: "client"` and `parent_id: <client_id>` in the JSON body)
  liberally; the search history then becomes a chat-friendly per-client
  journal.
- Respect PDPA: client memory is platform-encrypted and `scope=user`
  (agent-private). Do **not** write client data to `scope=chatgroup` and
  do not paste it into external services.
