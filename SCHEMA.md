---
name: authoring
description: Use this whenever the user wants to create, build, author, make, package, edit, update, or refine a capability or skill for this platform (e.g. "make me a capability", "turn this into a skill", "save this workflow as a capability", "build a skill that…", "edit my capability", "add an MCP to my capability", "wire a credential to my capability's MCP server"). Also use it proactively — without being asked — when you notice you have carried out the same multi-step workflow more than once and it is worth saving as a reusable skill (see Flow E). Loads the rules, interview flow, and full manifest schema for authoring a capability package.
---

# Capability Creator

You are guiding the user through authoring a **capability package** and writing it into the group files (artifacts). You interview the user, then create or edit the package files. You **stop once the package is drafted in the group files** — you never install it yourself. Initial installation is done by the user from the package card in the group-file UI.

Work through the existing group-file tools you already have: `create_artifact` (create a file), `read_artifact` (read one), `update_artifact` (edit precisely with `edits: [{old_string, new_string, replace_all}]` or replace `content`), and `list_artifacts` (see what exists). Files are addressed by path `/<topic>/<folder>/<title>`; the current topic is the working directory.

This file is also the platform's canonical, complete definition of the capability manifest format — the flows below draft one specific shape (a package inside the group files), but the schema sections apply to every shape a capability can take, including ones published straight to a GitHub repo (see **Reference** near the end).

## Package layout

A capability package is a folder in the group files with this layout:

- `<package>/.chubbyclaw/capability.json` — **manifest (required)**
- `<package>/skills/<skill-name>/SKILL.md` — **one file per skill**, with YAML frontmatter
- `<package>/.mcp.json` — optional MCP server declarations (see MCP section for the real constraint)
- `<package>/references/`, `<package>/scripts/` — optional supporting files

### Manifest — `.chubbyclaw/capability.json`

```json
{
  "name": "my-capability",
  "description": "One clear sentence about what this capability is for.",
  "version": "1.0.0",
  "icon": "🧩",
  "credentials": [{ "name": "API_KEY", "type": "api_key" }]
}
```

| Field         | Required | Notes                                                                                                                                                                                   |
| ------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`        | yes      | kebab-case (lowercase letters, digits, hyphens only). This is the capability's **immutable identity** — renaming it is a brand-new capability, not a rename (see "Renaming" in Flow B). |
| `description` | yes      | One plain sentence — shown in the UI and injected into the agent's system prompt.                                                                                                       |
| `version`     | no       | Semver string, e.g. `"1.1.0"`. Defaults to `"1.0.0"` if omitted.                                                                                                                        |
| `icon`        | no       | A **single emoji** only. Anything that is not exactly one emoji is dropped.                                                                                                             |
| `credentials` | no       | API key / OAuth declarations this capability needs. See **Credentials** below. Omitting it entirely falls back to free-form env overrides.                                              |

There is no `author` field — a `capability.json` with one is not rejected, but nothing reads it; don't tell a user it will show up anywhere.

### Skill files — `skills/<skill-name>/SKILL.md`

```markdown
---
name: <skill-name>
description: Use when … (write the trigger clearly — this is what decides when the skill loads)
---

<the skill body: the instructions, workflow, or knowledge the agent should follow>
```

- The frontmatter `name` **must exactly match the directory name** `<skill-name>`.
- The frontmatter `description` **is required**. Write it as a strong "use when…" trigger — a vague description means the skill will not be picked when it should be.
- The body is the actual reusable instructions.

### MCP servers — `.mcp.json`

```json
{
  "<server-name>": { "type": "http", "url": "https://mcp.example.com/api" }
}
```

Standard MCP JSON-RPC config; a single file can define multiple servers. A group-files package entry recognizes exactly `type` / `url` / `command` — nothing else, and **no `credential` field** (see **Credentials** below for the real way to wire auth).

- **HTTP MCP (recommended, works in a package):** `{ "type": "http", "url": "..." }` — installs and works.
- **stdio MCP (npx / uvx):** do **not** write it into the package. The install pipeline maps every `.mcp.json` entry to an HTTP/URL server, so a stdio entry (a `command` with no `url`) would install as a broken, non-functional server. Tell the user: package `.mcp.json` currently supports only HTTP/URL MCP servers; a stdio MCP (e.g. `npx -y <pkg>` or `uvx <pkg>`) must be added after installation through the manual capability MCP form in the UI.
- If a server needs auth, wire it through `capability.json`'s `credentials[].mcps` — never through a key on the server entry itself. See **Credentials** below.

### Credentials — `credentials[]`

Each entry:

| Field          | Applies to   | Required                    | Notes                                                                                                                          |
| -------------- | ------------ | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `name`         | both         | yes                         | `api_key`: the env var name (e.g. `TAVILY_API_KEY`). `oauth`: a connection identifier (e.g. `GOOGLE_OAUTH`).                   |
| `type`         | both         | yes                         | exactly `"api_key"` or `"oauth"`.                                                                                              |
| `provider`     | `oauth` only | yes                         | `"google"`, `"github"`, `"slack"`, `"notion"`, `"gitlab"`, or `"custom"`.                                                      |
| `scopes`       | `oauth` only | conditional                 | OAuth scopes to request. **Required if `mcps` is non-empty**, unless the provider has no scope concept (today: only `notion`). |
| `mcps`         | `oauth` only | no                          | **Which `.mcp.json` server(s) this credential authorizes.** See below — this is the field that actually wires auth to a call.  |
| `required`     | both         | no                          | Whether the capability needs this credential to run. Defaults to `true`.                                                       |
| `description`  | both         | no                          | Human-readable text shown in the credential picker.                                                                            |
| `help_url`     | `api_key`    | no                          | Link to where the user gets the key.                                                                                           |
| `oauth_config` | `oauth`      | only if `provider:"custom"` | Custom provider's endpoints — see below.                                                                                       |

#### `mcps` — wiring a credential to a remote MCP server (read this before adding any OAuth-backed MCP)

`mcps` is a `string[]` naming keys from `.mcp.json`. It means "this credential's access token may be sent to these remote MCP servers." **This is the only place a credential↔server link is declared — `.mcp.json` server entries do not carry credential information themselves.**

A worked example — a capability with two remote servers behind one Google credential:

`.chubbyclaw/capability.json`:

```
{
  "name": "google-workspace",
  "credentials": [
    {
      "name": "GOOGLE_OAUTH",
      "type": "oauth",
      "provider": "google",
      "scopes": [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.readonly"
      ],
      "mcps": ["google-calendar", "google-gmail"]
    }
  ]
}
```

`.mcp.json` — server entries never mention the credential; the names just have to match:

```
{
  "google-calendar": { "type": "http", "url": "https://calendarmcp.googleapis.com/mcp/v1" },
  "google-gmail": { "type": "http", "url": "https://gmailmcp.googleapis.com/mcp/v1" }
}
```

Once installed, every call to a server listed in `mcps` automatically carries `Authorization: Bearer <token>` from the bound credential, refreshed as needed. Servers **not** listed in any credential's `mcps` get no auth header at all — that is the correct behavior for public/unauthenticated MCP servers, not a bug.

**Common mistake — do not repeat this:** putting a `"credential": "GOOGLE_OAUTH"` key inside a `.mcp.json` server entry instead of declaring `mcps` in `capability.json`. `.mcp.json` entries only recognize `type` / `url` / `command`; any other key, including `credential`, is silently dropped at install time. The server's auth stays wired to nothing, every call goes out with **no** `Authorization` header, and the remote server correctly returns 401 — no matter how many times the user re-binds the credential in the UI, because the credential was never actually attached to that server in the first place. If you see repeated 401s from a remote MCP server after the user says the credential is connected, check `capability.json` for a missing/incomplete `mcps` array before suspecting the credential itself.

Validation at install time (violating any of these gets the install rejected with a message naming the offending credential/server):

| Rule                                                                                                                            |
| ------------------------------------------------------------------------------------------------------------------------------- |
| every name in `mcps` must exist as a key in `.mcp.json`                                                                         |
| a given `.mcp.json` server name can be claimed by at most one credential                                                        |
| `type:"oauth"` + `mcps` non-empty ⇒ `scopes` must be non-empty (exempt only for providers with no scope concept, e.g. `notion`) |

`type:"api_key"` credentials are not subject to the scopes rule and are not currently wired to remote MCP servers via `mcps` — they're injected as env vars into the capability's process/container as before.

#### Custom OAuth provider (`oauth_config`)

When `provider` is `"custom"`, supply the endpoints directly:

```
{
  "name": "MY_SERVICE",
  "type": "oauth",
  "provider": "custom",
  "oauth_config": {
    "authorize_url": "https://my-service.com/oauth/authorize",
    "token_url": "https://my-service.com/oauth/token",
    "client_id_env": "MY_SERVICE_CLIENT_ID"
  }
}
```

The user supplies `client_id` / `client_secret` themselves via an env override; the platform does not have a client of its own for unknown services.

## Flow A — Create a new capability

Interview the user, one topic at a time, then write the files.

1. **Name & display name** — a kebab-case `name` (immutable identity) and a human-readable display name.
2. **Description** — one sentence: what is this capability for?
3. **When to use** — when should the agent reach for this? Turn their answer into the skill's frontmatter `description`.
4. **Body** — what should the skill actually make the agent do? Capture their workflow/instructions as the SKILL.md body.
5. **MCP server?** — ask if it needs one. If yes, also ask whether it needs a credential (API key or OAuth) and which server(s) it should apply to — follow **MCP servers** and **Credentials** above.
6. **Write the files** — pick the group + topic + folder with the user, then use `create_artifact`/`update_artifact` to write `.chubbyclaw/capability.json` and `skills/<name>/SKILL.md` (and `.mcp.json` if applicable) under `<package>/…`.
7. **Self-check, then hand off** — run the self-check below, then tell the user to review the files and **install the package from its card in the group files**. Do not install it yourself.

## Flow B — Edit an existing package draft

1. **Read first.** Use `list_artifacts`/`read_artifact` to see the current package folder and its files before changing anything. Never blind-write.
2. **Make precise edits.** Use `update_artifact` with `edits: [{old_string, new_string}]` for targeted changes; replace whole `content` only when rewriting a file.
3. **Renaming.** If the user wants to rename the capability, tell them plainly: the manifest `name` is the capability's identity, so renaming is treated as a **new capability**, not an in-place rename. Keep the original `name`, or create a new package under the new name.
4. **If the capability is already installed** by this user: after you finish editing the package files, call `update_installed_capability` with the manifest `name` to apply the changes. Do **not** ask the user to reinstall it.
5. **Debugging a 401/403 from a remote MCP server** — re-read `capability.json`'s `credentials[].mcps` first. A missing or wrong entry there (not the credential binding itself) is the most common cause — see the common-mistake callout under **Credentials** above.

## Flow C — Fork an installed capability, then edit

To base a new version on a capability the user already installed:

1. Fork it back into the group files as an editable draft using the existing fork-to-group action (this pulls the installed package's files into a group-file folder).
2. Then continue with **Flow B** on the resulting draft.
3. **Platform-owned capabilities cannot be forked** (they have no group-file source). If the user asks to fork one, say so clearly instead of trying.

## Flow D — Attach an MCP server (configure only, never build)

You only **configure** an MCP server reference; you never write MCP server code. Follow **MCP servers** and, if it needs auth, **Credentials** above for the exact format. If the user asks you to **write a new MCP server**, explain that this wizard only wires up existing MCP servers by configuration and does not generate server code.

## Flow E — Proactively propose crystallizing a repeated workflow

Sometimes nobody asks you to make a skill, but you notice you have just worked out a
useful multi-step procedure — and you (or a teammate) will likely repeat it. You **may**
propose crystallizing it into a reusable skill, on your own initiative.

A proposal is **exactly a draft package** (Flow A), nothing more:

1. Briefly tell the user what you noticed ("we've done X→Y→Z a few times; want me to save it
   as a reusable skill?") and draft the package into the group files with the normal tools.
2. **It is only a proposal until the user applies it.** Drafting the files does **not** make
   the skill active or callable. The capability starts working only after the user installs it
   from the package card in the group-file UI — you never install it, and you cannot use the
   proposed skill until they do.
3. If the user is not interested, leave the draft or offer to delete it; do not push. An
   un-applied proposal simply stays a draft and never takes effect.

Only propose when the workflow is genuinely reusable — do not draft a package for a one-off task.

## Reference — repository shapes beyond the group files

Everything above drafts a capability **inside the group files**, for the user to install locally. A capability can also live in its own GitHub repository (a single capability, or a marketplace of many) — you'll never write these files through this wizard, but you should recognize and explain them correctly if asked.

### Repository shapes, checked in this order (first match wins)

| Path checked                                                               | Recognized as     | Notes                           |
| -------------------------------------------------------------------------- | ----------------- | ------------------------------- |
| `.chubbyclaw/marketplace.json`                                             | Marketplace       | native format                   |
| `.chubbyclaw/capability.json`                                              | Capability        | native format                   |
| `.claude-plugin/marketplace.json`                                          | Marketplace       | Claude Code compatibility       |
| `.claude-plugin/plugin.json`                                               | Capability        | Claude Code compatibility       |
| `.cursor-plugin/marketplace.json`                                          | Marketplace       | Cursor compatibility            |
| `.cursor-plugin/plugin.json`                                               | Capability        | Cursor compatibility            |
| _(none of the above; falls back to searching for)_ any `skills/*/SKILL.md` | Skills Collection | bare skills, no manifest needed |

Note this is a flat, ordered list, not "all Marketplace paths, then all Capability paths" — a repo with `.chubbyclaw/capability.json` is detected as Capability even if it also happens to carry a `.claude-plugin/marketplace.json`, since the native path is checked first.

### `marketplace.json` (repo root, multi-capability repos only)

```json
{
  "name": "my-marketplace",
  "description": "Short description of this collection.",
  "capabilities": [
    {
      "name": "my-capability",
      "description": "What this capability does.",
      "source": "./capabilities/my-capability",
      "version": "1.0.0"
    }
  ]
}
```

| Field                        | Required | Notes                                  |
| ---------------------------- | -------- | -------------------------------------- |
| `name`                       | yes      | unique identifier for this marketplace |
| `description`                | yes      | human-readable summary                 |
| `capabilities[].name`        | yes      | kebab-case unique id                   |
| `capabilities[].description` | yes      | one-line UI summary                    |
| `capabilities[].source`      | yes      | see **Source types** below             |
| `capabilities[].version`     | no       | semver, shown in the UI                |

Extra top-level or per-entry fields (`owner`, `category`, `author`, `homepage`, `tags`, `keywords`, …) are not an error, but nothing currently reads them — don't promise a user they'll show up anywhere in the UI.

**Source types:**

```
"source": "./capabilities/my-capability"                                                              // same-repo relative path
"source": { "type": "github", "repo": "owner/repo" }                                                  // whole external repo, tracks its default branch
"source": { "type": "url", "url": "https://github.com/owner/repo.git", "sha": "abc123" }              // whole repo; sha optional, pins the install to that commit
"source": { "type": "git-subdir", "url": "https://github.com/owner/repo.git", "path": "capabilities/my-capability", "sha": "abc123" }  // one subdirectory of an external repo
```

### Directory layouts

**Marketplace repo:**

```
<repo-root>/
├── .chubbyclaw/marketplace.json
├── capabilities/
│   ├── <capability-a>/{.chubbyclaw/capability.json, skills/, .mcp.json}
│   └── <capability-b>/...
└── README.md
```

**Single-capability repo:**

```
<repo-root>/
├── .chubbyclaw/capability.json
├── skills/...
├── .mcp.json
└── README.md
```

Both follow the same directory-convention discovery as the group-files package above — nothing needs to be declared beyond `.chubbyclaw/capability.json`, `skills/`, and `.mcp.json`.

## Self-check before handing off

Before telling the user the package is ready:

1. `list_artifacts` the package folder and confirm `.chubbyclaw/capability.json` and at least one `skills/<name>/SKILL.md` exist.
2. Re-read the manifest: `name` is kebab-case, `description` present, `icon` (if any) is a single emoji.
3. If `credentials` is present: every `oauth` entry with a non-empty `mcps` has non-empty `scopes` (unless the provider has no scope concept), every name in every `mcps` array exists as a key in `.mcp.json`, and no `.mcp.json` server is claimed by more than one credential.
4. Re-read each SKILL.md: frontmatter `name` matches its directory, `description` present and written as a clear "use when…".
5. Only then tell the user to install it from the package card.

## Hard rules

- **Draft and edit only.** Never install a package yourself — initial installation requires the user's explicit confirmation in the UI. The only apply-without-UI case is `update_installed_capability` for a package the user has **already** installed (Flow B step 4).
- **Stop at the group files.** Your job ends when the package is correctly drafted/edited in the artifacts.
- **Keep the identity stable.** Never silently change a manifest `name`.
- **Credential wiring lives in `capability.json`, never in `.mcp.json`.** A `credential` (or similarly named) key on a `.mcp.json` server entry does nothing but get silently dropped — always use `credentials[].mcps`.
