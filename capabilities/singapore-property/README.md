# singapore-property

Singapore residential property decision assistant. Three role-aware workflows (buyer / seller / agent) backed by the `sgprop` MCP server (URA + HDB + rental data) and local policy calculators.

## What it does

- **Buyer**: eligibility check (ABSD/TDSR/MSR), needs collection, project shortlisting, valuation, tax & holding-cost summary
- **Seller**: CMA valuation, sale-cost computation (SSD, agent fees), pricing strategy, listing tracker
- **Agent**: per-client profile/holdings/candidates, batch matching, viewing routes, funnel tracking

## How it works

- The skill router (`skills/sg-property/SKILL.md`) detects which role applies and pulls in the right reference.
- Data queries go through the `sgprop` MCP tools (`sgprop_search_projects`, `sgprop_project_report`, `sgprop_transactions`, `sgprop_supply_outlook`, `sgprop_location_context`).
- Tax / loan / yield computations use deterministic Python scripts under `skills/sg-property/scripts/`.
- Personal data (`profile`, `holdings`, `candidates`, `clients`) is persisted under `~/.config/sgprop/` via the `mem.py` CLI — never written directly.

## Requirements

- `python3` 3.10+ on PATH
- ChubbyClaw account with access to `https://chubbyclaw.com/mcp/sgprop`

## Privacy

Memory files store financial and identity data (income, CPF, NRIC nationality, addresses). They are written with `0600` permissions and never sent to any external service. v1 does not encrypt them — keep your machine secure.

See `../../docs/superpowers/specs/2026-05-04-sg-property-design.md` for the full design.
