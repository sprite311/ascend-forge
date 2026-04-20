# Adapter · Claude Code

> 把 Ascend-Forge 运行在 Claude Code 上所需的胶水（很少，因为 Claude Code 的 agents/skills 规范就是本项目的母体）。

## 工作原理

1. Claude Code 自动读 `CLAUDE.md`（repo 根）。
2. `CLAUDE.md` 中的 subagent 引用（`@ascend-adapter` 等）被解析到 `agents/*.md`。
3. `skills/*/SKILL.md` 的 `trigger` 由主 agent 按命中选择性加载。
4. `rules/ACTIVE.md` 由主 agent 每次开场全量加载。
5. `.agent/config.yaml` 不被 Claude Code 原生解析，但**你的主 agent prompt** 需要知道其语义（已写在 `CLAUDE.md` 和 `.agent/system_prompt.md`）。

## 推荐设置（可选）

`.claude/settings.json`：

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(npu-smi:*)",
      "Bash(msprof:*)",
      "Bash(python:*)",
      "Bash(pip:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(dd:*)",
      "Bash(modprobe:*)",
      "Bash(rmmod:*)"
    ]
  }
}
```

## 运行自检

```
用户: 列出你能调用的 subagents
期望: 列出 agents/ 下全部 7 个
```

```
用户: 我昇腾 910B×8 要部署 Qwen2-72B
期望: 主 agent 路由到 @ascend-deployer，并引用 wiki/playbooks/ / skills/mindie-deployment/
```

## 工具能力映射（无需映射，名字一致）

| 抽象能力 | Claude Code 工具 |
|---|---|
| shell | `Bash` |
| read_file | `Read` |
| write_file | `Write` |
| edit_file | `Edit` |
| list_files | `Glob` |
| search | `Grep` |

## 常见问题

- **subagent 不被路由**：检查 `agents/<name>.md` 的 frontmatter `name:` 与文件名一致（不带 `.md`）。
- **skill 不触发**：`trigger:` 词过泛或过窄。建议 2–5 个关键词，覆盖中英文。
- **进化不发生**：确认 `CLAUDE.md` 的"进化铁律"段是否被主 agent 看到；可以在对话里显式请求 `@knowledge-curator` 收尾。
