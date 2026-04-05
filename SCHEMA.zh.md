# ChubbyClaw Capability Marketplace — Schema 参考

本文档是 ChubbyClaw Capability Marketplace Schema 的权威参考，涵盖仓库类型识别、市场清单（`marketplace.json`）、Capability 清单（`capability.json`）以及 Capability 目录布局约定。

---

## 仓库类型

ChubbyClaw 按以下优先级识别仓库类型：

| 优先级 | 类型 | 识别条件 | 说明 |
|--------|------|----------|------|
| 1 | **Marketplace** | 存在 `.chubbyclaw/marketplace.json` | 多 Capability 集合仓库 |
| 2 | **Capability** | 存在 `.chubbyclaw/capability.json` | 单个独立 Capability |
| 3 | **Skills Collection** | 存在任意 `skills/*/SKILL.md` | 裸 Skills 集合，无需 Manifest |

### 兼容性

ChubbyClaw 在检查 `.chubbyclaw/` 后，还会按顺序识别 Claude Code（`.claude-plugin/`）和 Cursor（`.cursor-plugin/`）格式的仓库。

---

## 市场清单 — `marketplace.json`

位置：仓库根目录的 `.chubbyclaw/marketplace.json`。

```json
{
  "name": "my-marketplace",
  "description": "这个集合的简短描述。",
  "owner": {
    "name": "作者或组织名",
    "email": "contact@example.com"
  },
  "capabilities": [
    {
      "name": "my-capability",
      "description": "这个 Capability 的功能。",
      "source": "./capabilities/my-capability"
    }
  ]
}
```

### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 此 Marketplace 的唯一标识符 |
| `description` | string | 是 | 人类可读的摘要 |
| `owner` | object | 是 | 见下方 |
| `capabilities` | array | 是 | Capability 条目列表（见下方）|

**`owner` 字段：**

| 字段 | 类型 | 必填 |
|------|------|------|
| `name` | string | 是 |
| `email` | string | 否 |

---

### Capability 条目字段

`capabilities` 数组中每个条目的字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 唯一标识符（kebab-case）|
| `description` | string | 是 | 显示在 UI 中的一行摘要 |
| `source` | string 或 object | 是 | 获取此 Capability 的来源（见 Source 类型）|
| `category` | string | 否 | 下方分类之一 |
| `version` | string | 否 | 语义版本号，如 `"1.2.0"` |
| `author` | object | 否 | `{ "name": "...", "email": "..." }` |
| `homepage` | string | 否 | 文档或项目地址 |
| `tags` | string 数组 | 否 | 如 `["community-managed"]` |
| `keywords` | string 数组 | 否 | 搜索关键词 |

#### Source 类型

**同仓库 Capability**（字符串简写）：
```json
"source": "./capabilities/my-capability"
```
指向同一仓库内 Capability 目录的相对路径。

**外部 GitHub 仓库**（整个仓库作为一个 Capability）：
```json
"source": {
  "type": "github",
  "repo": "owner/repo"
}
```

**外部 Git URL**（整个仓库）：
```json
"source": {
  "type": "url",
  "url": "https://github.com/owner/repo.git",
  "sha": "abc123def456"
}
```
`sha` 锁定安装版本；省略则始终跟踪默认分支。

**外部仓库的子目录**：
```json
"source": {
  "type": "git-subdir",
  "url": "https://github.com/owner/repo.git",
  "path": "capabilities/my-capability",
  "ref": "main",
  "sha": "abc123def456"
}
```

#### 分类

`development` · `productivity` · `security` · `database` · `deployment` · `design` · `learning` · `math` · `testing` · `monitoring` · `automation` · `migration` · `location`

---

## Capability 清单 — `capability.json`

位置：Capability 目录内的 `.chubbyclaw/capability.json`。

Manifest 有意保持极简。Capability 的内容（skills、MCP Server）通过目录约定自动发现，无需在 Manifest 中声明。

```json
{
  "name": "my-capability",
  "description": "这个 Capability 的功能，以及何时使用它。",
  "author": {
    "name": "作者名",
    "email": "author@example.com"
  }
}
```

### 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 唯一标识符（kebab-case）|
| `description` | string | 是 | 显示在 UI 中，并注入到 Agent 的 system prompt |
| `author` | object | 否 | `{ "name": "...", "email": "...", "url": "..." }` |

---

## Capability 目录布局

所有内容从 Capability 根目录按约定自动发现，无需在 `capability.json` 中声明路径。

```
<capability-root>/
├── .chubbyclaw/
│   └── capability.json      # 必须：Capability 清单
│
├── skills/                  # 可选：Agent Skills（认知层）
│   └── <skill-name>/
│       └── SKILL.md         # 每个 Skill 必须：YAML frontmatter + 指令正文
│
├── .mcp.json                 # 可选：MCP Server 配置（行动层）
│
└── README.md                # 建议：人类可读文档
```

### `skills/<skill-name>/SKILL.md`

`skills/` 下每个子目录对应一个 Skill，包含一个带 YAML frontmatter 的 `SKILL.md` 文件。ChubbyClaw 遵循 [Agent Skills 开放标准](https://agentskills.io/specification)。

```markdown
---
name: skill-name
description: "这个 Skill 的功能，以及 Agent 应在何时调用它。"
---

完整的 Skill 指令正文...
```

| Frontmatter 字段 | 必填 | 说明 |
|------------------|------|------|
| `name` | 是 | 必须与父目录名一致 |
| `description` | 是 | 注入到 Agent system prompt，供 Skill 发现使用 |

### `.mcp.json`

Capability 根目录下的 MCP Server 配置：

```json
{
  "<server-name>": {
    "type": "http",
    "url": "https://mcp.example.com/api"
  }
}
```

遵循标准 MCP JSON-RPC 配置格式，单个文件可定义多个 Server。

---

## Marketplace 仓库目录布局

包含多个 Capability 的仓库：

```
<repo-root>/
├── .chubbyclaw/
│   └── marketplace.json     # 必须：列出所有 Capability
│
├── capabilities/            # 所有 Capability 统一放在此目录
│   ├── <capability-a>/
│   │   ├── .chubbyclaw/
│   │   │   └── capability.json
│   │   ├── skills/
│   │   │   └── ...
│   │   └── .mcp.json
│   │
│   └── <capability-b>/
│       └── ...
│
└── README.md
```

---

## 单 Capability 仓库目录布局

仓库本身即一个 Capability：

```
<repo-root>/
├── .chubbyclaw/
│   └── capability.json      # 必须：Capability 清单，位于仓库根目录
│
├── skills/
│   └── ...
├── .mcp.json
└── README.md
```

---

## 兼容性矩阵

| 仓库格式 | 识别为 | 说明 |
|----------|--------|------|
| `.chubbyclaw/marketplace.json` | Marketplace | ChubbyClaw 原生格式 |
| `.chubbyclaw/capability.json` | Capability | ChubbyClaw 原生格式 |
| `.claude-plugin/marketplace.json` | Marketplace | 兼容 Claude Code 格式 |
| `.claude-plugin/plugin.json` | Capability | 兼容 Claude Code 格式 |
| `.cursor-plugin/marketplace.json` | Marketplace | 兼容 Cursor 格式 |
| `.cursor-plugin/plugin.json` | Capability | 兼容 Cursor 格式 |
| 存在 `skills/*/SKILL.md` | Skills Collection | 无需 Manifest |
