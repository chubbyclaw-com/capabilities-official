# ChubbyClaw Capability Marketplace — Schema Reference

This document is the authoritative reference for the ChubbyClaw capability marketplace schema. It covers repository detection, the marketplace manifest (`marketplace.json`), the capability manifest (`capability.json`), and the capability directory layout conventions.

---

## Repository Types

ChubbyClaw detects three types of repositories, in priority order:

| Priority | Type | Detection | Description |
|----------|------|-----------|-------------|
| 1 | **Marketplace** | `.chubbyclaw/marketplace.json` exists | A collection of multiple capabilities |
| 2 | **Capability** | `.chubbyclaw/capability.json` exists | A single standalone capability |
| 3 | **Skills Collection** | Any `skills/*/SKILL.md` found | Bare skills, no manifest required |

### Compatibility

ChubbyClaw also accepts repositories using the Claude Code (`.claude-plugin/`) and Cursor (`.cursor-plugin/`) manifest conventions. Detection falls through to these after checking `.chubbyclaw/`.

---

## Marketplace Manifest — `marketplace.json`

Location: `.chubbyclaw/marketplace.json` at the repository root.

```json
{
  "name": "my-marketplace",
  "description": "A short description of this collection.",
  "owner": {
    "name": "Author or Organization",
    "email": "contact@example.com"
  },
  "capabilities": [
    {
      "name": "my-capability",
      "description": "What this capability does.",
      "source": "./my-capability"
    }
  ]
}
```

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for this marketplace |
| `description` | string | Yes | Human-readable summary |
| `owner` | object | Yes | See below |
| `capabilities` | array | Yes | List of capability entries (see below) |

**`owner` fields:**

| Field | Type | Required |
|-------|------|----------|
| `name` | string | Yes |
| `email` | string | No |

---

### Capability Entry Fields

Each item in the `capabilities` array:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier (kebab-case) |
| `description` | string | Yes | One-line summary shown in UI |
| `source` | string or object | Yes | Where to fetch this capability (see Source Types) |
| `category` | string | No | One of the categories below |
| `version` | string | No | Semver, e.g. `"1.2.0"` |
| `author` | object | No | `{ "name": "...", "email": "..." }` |
| `homepage` | string | No | Documentation or project URL |
| `tags` | array of strings | No | e.g. `["community-managed"]` |
| `keywords` | array of strings | No | Search terms |

#### Source Types

**Same-repository capability** (string shorthand):
```json
"source": "./capabilities/my-capability"
```
A relative path to the capability directory within the same repository.

**External GitHub repository** (full repo as one capability):
```json
"source": {
  "type": "github",
  "repo": "owner/repo"
}
```

**External Git URL** (full repo):
```json
"source": {
  "type": "url",
  "url": "https://github.com/owner/repo.git",
  "sha": "abc123def456"
}
```
`sha` pins the installed version; omit to always track the default branch.

**Subdirectory of an external repository**:
```json
"source": {
  "type": "git-subdir",
  "url": "https://github.com/owner/repo.git",
  "path": "capabilities/my-capability",
  "ref": "main",
  "sha": "abc123def456"
}
```

#### Categories

`development` · `productivity` · `security` · `database` · `deployment` · `design` · `learning` · `math` · `testing` · `monitoring` · `automation` · `migration` · `location`

---

## Capability Manifest — `capability.json`

Location: `.chubbyclaw/capability.json` inside a capability directory.

The manifest is intentionally minimal. Capability contents (skills, MCP servers) are discovered from the directory layout, not declared in the manifest.

```json
{
  "name": "my-capability",
  "description": "What this capability does and when to use it.",
  "author": {
    "name": "Author Name",
    "email": "author@example.com"
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier (kebab-case) |
| `description` | string | Yes | Summary shown in UI and injected into agent system prompt |
| `author` | object | No | `{ "name": "...", "email": "...", "url": "..." }` |

---

## Capability Directory Layout

All capability contents are discovered by convention from the capability root. No paths need to be declared in `capability.json`.

```
<capability-root>/
├── .chubbyclaw/
│   └── capability.json      # Required: capability manifest
│
├── skills/                  # Optional: agent skills (cognitive layer)
│   └── <skill-name>/
│       └── SKILL.md         # Required per skill — YAML frontmatter + instructions
│
├── mcp.json                 # Optional: MCP server configuration (action layer)
│
└── README.md                # Recommended: human-readable docs
```

### `skills/<skill-name>/SKILL.md`

Each skill is a directory under `skills/` containing a `SKILL.md` file with YAML frontmatter. ChubbyClaw follows the [Agent Skills open standard](https://agentskills.io/specification).

```markdown
---
name: skill-name
description: "What this skill does and WHEN the agent should invoke it."
---

Full skill instructions here...
```

| Frontmatter Field | Required | Description |
|-------------------|----------|-------------|
| `name` | Yes | Must match the parent directory name |
| `description` | Yes | Shown in agent system prompt for skill discovery |

### `mcp.json`

MCP server configuration at the capability root:

```json
{
  "<server-name>": {
    "type": "http",
    "url": "https://mcp.example.com/api"
  }
}
```

Follows the standard MCP JSON-RPC configuration format. Multiple servers may be defined in a single file.

---

## Marketplace Repository Layout

A repository that hosts multiple capabilities:

```
<repo-root>/
├── .chubbyclaw/
│   └── marketplace.json     # Required: lists all capabilities
│
├── capabilities/            # All capabilities live here
│   ├── <capability-a>/
│   │   ├── .chubbyclaw/
│   │   │   └── capability.json
│   │   ├── skills/
│   │   │   └── ...
│   │   └── mcp.json
│   │
│   └── <capability-b>/
│       └── ...
│
└── README.md
```

---

## Single-Capability Repository Layout

A repository that is itself one capability:

```
<repo-root>/
├── .chubbyclaw/
│   └── capability.json      # Required: capability manifest at repo root
│
├── skills/
│   └── ...
├── mcp.json
└── README.md
```

---

## Compatibility Matrix

| Repo Format | Detected As | Notes |
|-------------|-------------|-------|
| `.chubbyclaw/marketplace.json` | Marketplace | Native ChubbyClaw format |
| `.chubbyclaw/capability.json` | Capability | Native ChubbyClaw format |
| `.claude-plugin/marketplace.json` | Marketplace | Claude Code compatible |
| `.claude-plugin/plugin.json` | Capability | Claude Code compatible |
| `.cursor-plugin/marketplace.json` | Marketplace | Cursor compatible |
| `.cursor-plugin/plugin.json` | Capability | Cursor compatible |
| `skills/*/SKILL.md` present | Skills Collection | No manifest required |
