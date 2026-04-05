# capabilities-official

Official ChubbyClaw-managed directory of high quality capabilities.

## Schema

- [SCHEMA.md](./SCHEMA.md) — Schema reference (English)
- [SCHEMA.zh.md](./SCHEMA.zh.md) — Schema 参考（中文）

The schema covers repository detection, the marketplace manifest (`marketplace.json`), the capability manifest (`capability.json`), and the capability directory layout conventions.

## Adding a Capability

To add a capability to this marketplace:

1. Create a directory under `capabilities/`
2. Add `.chubbyclaw/capability.json` with `name`, `description`, and `author`
3. Add skills under `skills/<skill-name>/SKILL.md`
4. Add MCP tools in `mcp.json` (if applicable)
5. Add an entry to `.chubbyclaw/marketplace.json`

See `capabilities/example-capability/` for a complete reference.
