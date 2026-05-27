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
- Personal data (`profile`, `holding`, `candidate`, `client`, viewings, offers, notes) is persisted via the ChubbyClaw platform's native memory tools (`MemoryWrite / MemoryGet / MemorySearch / MemoryList / MemoryDelete`). Default `scope=user`; see `skills/sg-property/references/memory-conventions.md` for the record envelope and update protocol.

## Requirements

- `python3` 3.10+ on PATH (only needed when running the `calc_*.py` scripts)
- ChubbyClaw account with access to `https://chubbyclaw.com/mcp/sgprop`

## Privacy

Personal data (income, CPF, NRIC nationality, addresses, clients) is stored in the ChubbyClaw platform memory store: AES-256-GCM at rest with a per-subject DEK, `scope=user` so only you can read it, and crypto-shred on account or group deletion. Skills never write `scope=chatgroup` without an explicit user request, and only the group owner can write group-level memory.

See `../../docs/superpowers/specs/2026-05-04-sg-property-design.md` for the full design.
