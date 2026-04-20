# 跨平台迁移指南 (Porting Guide)

> 目标：ascend-forge 的**同一份知识与 agent 定义**，在 Claude Code、openclaw、OpenHands/OpenDevin、Cursor、Cline、裸 LLM API 上都能跑。

---

## 1. 平台契约 (Platform Contract)

任何平台只要满足以下 3 条，就可以运行 ascend-forge：

| 能力 | 说明 | 等价物示例 |
|---|---|---|
| **Shell** | 能执行任意 bash | Claude Code `Bash` / OpenHands `run` / MCP `shell` |
| **File IO** | 能读写仓库内任意文件 | `Read/Write/Edit` / `open`+`fs.write` |
| **Subagent OR Prompt chaining** | 能调"另一个角色"或至少能链式 prompt | Claude Code `agents/*.md` / LangGraph nodes / openclaw roles |

缺任何一条的平台不支持（或只能降级跑"单 agent 模式"）。

---

## 2. 目录契约是移植面

所有"Agent 状态"都在仓库里，**平台只提供运行时**：

```
ascend-forge/
├── CLAUDE.md         ← Claude Code 入口
├── AGENTS.md         ← 中立入口（openclaw / Cursor / Cline / OpenHands）
├── agents/*.md       ← subagent 定义（同一份两边复用）
├── skills/**/SKILL.md
├── memory/
├── wiki/
├── cases/
├── rules/
└── adapters/
    ├── claude-code/  ← 平台特定胶水（能力映射、tool 命名差异）
    └── openclaw/
```

关键：**`agents/*.md` 是平台无关的**。平台差异只在入口文件和 `adapters/<平台>/` 里。

---

## 3. Claude Code

### 3.1 启动

把 ascend-forge 作为 repo 打开，Claude Code 会自动读 `CLAUDE.md`。
`CLAUDE.md` 会引用 `agents/` 下的 subagent，并在对话中通过 `@ascend-deployer` 等方式调用。

### 3.2 支持的约定

- `agents/<name>.md`（frontmatter + prompt）
- `skills/<name>/SKILL.md`
- `.claude/settings.json`（可选，对 hook / 允许命令做局部约束）

### 3.3 建议配置 (`.claude/settings.json`，可选)

```json
{
  "permissions": {
    "allow": ["Bash(git:*)", "Bash(npu-smi:*)", "Bash(msprof:*)"],
    "deny":  ["Bash(rm -rf:*)", "Bash(dd:*)"]
  }
}
```

### 3.4 常见问题

- **subagent 不被路由**：检查 `agents/<name>.md` 的 frontmatter `name` 字段与文件名一致。
- **skill 不触发**：`skills/<name>/SKILL.md` 的 `trigger:` 要有足够具体的词，避免太泛。

详见 [`adapters/claude-code/README.md`](../adapters/claude-code/README.md)。

---

## 4. openclaw

> 注：openclaw 当前能力以 `AGENTS.md` + 文件化 memory 为主。下列为基于其公开约定的推荐做法，具体以所用版本为准。

### 4.1 启动

- 入口文件：`AGENTS.md`（本仓库已提供）
- `AGENTS.md` 里显式列出 subagent 文件路径，openclaw 会把它们当 persona prompts 加载。

### 4.2 工具命名差异

| 抽象能力 | Claude Code | openclaw |
|---|---|---|
| 运行 shell | `Bash` | `shell` / `run` |
| 读文件 | `Read` | `read_file` / `fs.read` |
| 写文件 | `Write`/`Edit` | `write_file` / `edit` |

在 subagent prompt 里**用能力名**（"run shell", "edit file"），不要硬编码工具名，由 adapter 层翻译。

### 4.3 适配胶水

`adapters/openclaw/tools.md` 提供一张映射表；如需 MCP 桥，再加 `adapters/openclaw/mcp.json`。

---

## 5. OpenHands / OpenDevin

- 把 `AGENTS.md` 作为 repo 级"persona"；把 `agents/*.md` 作为多 agent 切换的脚本。
- 推荐用 Micro-Agents 方式：一个主 agent + 在 `agents/` 下按需 spawn。
- 工具桥：OpenHands 的 `BashSession` 对应 `Bash`；`FileEditor` 对应 `Read/Write/Edit`。
- 如果用 OpenHands 的"knowledge" 能力，可让它**额外**指向 `wiki/` 做 RAG，但**不要**替换本项目的 wiki—— wiki 是源头，RAG 是派生。

---

## 6. Cursor / Cline

两者都支持 `AGENTS.md`（或 `.cursor/rules/`、`.clinerules/`）。推荐：

- `AGENTS.md` 为主，短小。
- 在 `.cursor/rules/` 或 `.clinerules/` 下放软链或复制 `rules/ACTIVE.md`。
- Cursor 的 `/skills` 能力可直接复用 `skills/**/SKILL.md` 的 trigger 设计（Cursor 用 glob，需要在 adapter 里翻译）。

---

## 7. 裸 LLM API / LangGraph

- 写 `adapters/<你的>/bootstrap.py`：
  1. 把 `AGENTS.md` + `rules/ACTIVE.md` + 命中的 wiki/memory 拼成 system prompt。
  2. 把 `agents/*.md` 作为 sub-node 的 prompt。
  3. Tool 层自己实现 `bash`、`read_file`、`write_file`。
- 进化循环：手动或定时调用 `tools/evolve.py`。

---

## 8. 迁移自检清单

把 ascend-forge 搬到新平台后，跑这几步：

1. 在新平台里问："列出你现在能调用的 subagent"——应能列出 `agents/` 里的所有条目。
2. 让它回答一个简单的昇腾问题（如"910B 有多少 AICore？"），观察是否去读了 `wiki/hardware/910b.md`。
3. 触发一次 skill（如问"怎么起 MindIE 服务"），观察是否匹配到 `skills/mindie-deployment/SKILL.md`。
4. 结束后看 `cases/` 下是否新增一条归档（证明 curator 跑了）。
5. `git diff` 查看本次进化写入，人工审一次再 commit。

以上四步全过 → 迁移成功。
