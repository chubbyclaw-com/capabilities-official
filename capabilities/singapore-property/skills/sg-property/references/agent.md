# Agent workflow

Use this reference when the user is a property agent juggling multiple
clients. Many steps reuse the buyer/seller logic, but scoped to a client
record.

## 1. Client onboarding

`python3 scripts/mem.py clients list` — see existing clients.

For a new client:

```bash
python3 scripts/mem.py clients create --data '{
  "id": "tan-2026-05-08",
  "name": "Mr Tan",
  "role": "buyer",
  "status": "qualifying"
}'
```

`id` should be slug-safe (lowercase letters, digits, hyphens). A typical
pattern is `<surname>-<YYYY-MM-DD>`.

`role` is one of: `buyer`, `seller`, `both`.

## 2. Per-client profile + holdings + candidates

Every `mem.py holdings ...` and `mem.py candidates ...` command accepts a
`--client <id>` flag that scopes the operation to the client's file
instead of the user's global memory.

```bash
# Client's existing holding (for upgrade work)
python3 scripts/mem.py holdings add --client tan-2026-05-08 --data '{
  "address": "Block 123 Tampines St 11 #08-12",
  "type": "hdb",
  "purchase_date": "2015-04",
  "purchase_price_sgd": 480000
}'

# Client's candidate
python3 scripts/mem.py candidates add --client tan-2026-05-08 --data '{
  "project_name": "Bedok South Residences",
  "stage": "shortlist"
}'
```

Profile fields (income / nationality / preferences) live in the
`profile` substructure of the client file. Update it via
`mem.py clients update --id <client-id> --patch '{"profile":{...}}'`.

## 3. Client requirement gathering

- For buyer clients, work through the buyer workflow
  (`references/buyer.md`) but persist everything under `--client <id>`.
- For seller clients, work through the seller workflow
  (`references/seller.md`) similarly.
- For `role: both`, sequence: settle the sell side first (cash + ABSD
  refund timing), then the buy side.

## 4. Batch matching

When the agent says "5 clients, $2-3m, family upgrade":

1. `mem.py clients list` to find clients with that profile.
2. For each, read their `preferences` from the client file.
3. Run a single `sgprop_search_projects` with the union of constraints.
4. Score each project against each client (district match, school match,
   price band).
5. Output a matrix: clients × top 5 projects with green/yellow/red
   indicators.

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

Update via `mem.py clients update --id <id> --patch '{"status":"viewing"}'`.

A weekly funnel report:

```bash
python3 scripts/mem.py clients list
```

Group by status, count, and surface stale ones (no `updated_at` change in
> 14 days — chase up).

## 8. New launch tracking

Agents working a new launch want to monitor take-up:

```
sgprop_search_projects --status new_launch --district <d>
sgprop_project_report --project "<name>" --sections new_launch_progress,transactions
```

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
  in `profile.json` — saves them retyping.
- Use `mem.py notes append --target clients --client <id> --text "..."`
  liberally; the per-client file becomes a chat-friendly journal.
- Respect PDPA: client memory files are local and private. Don't paste
  them into external services.
