# capabilities-official

Official ChubbyClaw-managed directory of high quality capabilities.

## Schema

[SCHEMA.md](./SCHEMA.md) is the complete capability manifest schema: repository detection, the marketplace manifest (`marketplace.json`), the capability manifest (`capability.json`), credential declarations (including wiring a credential to a remote MCP server), and the capability directory layout conventions.

It is kept byte-for-byte identical to the "Capability Creator" wizard built into the ChubbyClaw platform — the same file drives both the in-app authoring flow and this reference, so there is exactly one place that can drift. `SCHEMA.zh.md` has been retired for the same reason (a hand-kept translation is a second copy that silently goes stale); its content now just points here.

## Adding a Capability

To add a capability to this marketplace:

1. Create a directory under `capabilities/`
2. Add `.chubbyclaw/capability.json` with `name` and `description`
3. If the capability needs API keys or OAuth connections, declare them in `credentials` (see the Credentials section in [SCHEMA.md](./SCHEMA.md))
4. Add skills under `skills/<skill-name>/SKILL.md`
5. Add MCP tools in `.mcp.json` (if applicable)
6. Add an entry to `.chubbyclaw/marketplace.json`

See [SCHEMA.md](./SCHEMA.md) for the complete directory layout reference.
