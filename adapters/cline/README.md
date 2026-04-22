# Adapter · Cline

> Cline（前 "Claude Dev"）是一个 VSCode 插件，提供带确认流的 agentic coding 体验。
> 它对本项目**最友好**的点：原生支持 `.clinerules` 全局规则 + 自定义 MCP 工具，
> 最不友好的点：**无**子 agent 概念，所有角色都由单一 agent 按 prompt 切换。

## 认知差异（与 Claude Code 对比）

| 维度 | Claude Code | Cline |
|-----|------------|-------|
| 入口文件 | `CLAUDE.md` | `.clinerules`（repo 根，纯 markdown） |
| 子 agent | `@agent-name` 原生 | **无**；用 `.clinerules/<role>.md` + 显式切换 |
| 工具 | Bash/Read/Write/Edit/Glob/Grep | 同构（read/write/command） + MCP |
| Auto-approve | 细粒度每工具可配 | 按"模式"粗粒度（act/plan/do） |
| 上下文 | 自动读 CLAUDE.md + 按需加载 | `.clinerules` 被前置到 system prompt |

## 集成步骤

### 1. 把 `CLAUDE.md` → `.clinerules`

**最简办法**：直接在 repo 根新建 `.clinerules/` 目录（Cline 0.8+ 支持目录形式），
把本项目文件映射过去：

```
.clinerules/
├── 00-root.md          # 来自 CLAUDE.md 前半截（身份 / 开场 SOP）
├── 10-subagents.md     # agents/*.md 合成，每个一段，带 "何时切换到 X 角色"
├── 20-evolution.md     # 来自 .agent/evolution_policy.md
├── 30-safety.md        # 危险命令禁令
└── 99-style.md         # 输出语言 / 代码注释风格
```

Cline 按文件名顺序载入，优先级前缀数字好管理。

### 2. 子 agent 角色切换

在 `10-subagents.md` 里这样写：

```markdown
## 角色切换规则

当用户问题命中下列关键词时，在回答开头声明"我现在作为 @X 回答"：

- 迁移 / torch_npu / 算子替换 → @ascend-adapter
- 部署 / MindIE / vLLM / 推理服务 → @ascend-deployer
- 调优 / 显存 / 量化 / profiling → @ascend-tuner
- 报错 / ACL / HCCL / OOM → @ascend-diagnoser
- 驱动 / CANN / 硬件 / npu-smi → @ascend-env-doctor
- 基准 / benchmark → @ascend-benchmarker
- 任务收尾 → @knowledge-curator

角色 prompt 见 `agents/<name>.md`，按切换时机**内化**（不需要真的加载文件）。
```

### 3. MCP 工具（可选，但推荐）

Cline 支持自定义 MCP server。把本项目的**三个最有用的工具**接上：

```json
// mcp-servers.json 片段
{
  "ascend-forge-evolve": {
    "command": "python3",
    "args": ["tools/evolve.py", "--apply"]
  },
  "ascend-forge-bench": {
    "command": "python3",
    "args": ["tools/bench.py", "--json"]
  },
  "ascend-forge-check-policy": {
    "command": "python3",
    "args": ["tools/check_policy.py", "--from-git", "--strict"]
  }
}
```

这样用户在 Cline 里可以直接 "/tool evolve"（具体语法按 Cline 版本核实）。

### 4. Auto-approve 安全配置

Cline 的 auto-approve 粒度比 Claude Code 粗。本项目的危险命令（见
`.agent/evolution_policy.md §safety.dangerous_command_patterns`）建议：

- **不要**把 "Execute commands" 设为 Always
- 至少保留 "破坏性命令"（rm -rf / dd / modprobe / npu-smi set reset）需要确认
- `tools/` 下的 Python 脚本可以设 Auto（它们本身就是只读或受控写入）

## 已知限制

1. **`rules/ACTIVE.md` 不自动分行加载**——整个 .clinerules 目录被拼成一个 prompt 段。
   超过 Cline 默认 context 限制时会被截断；建议 `ACTIVE.md` 控制在 <200 行。
2. **`/evolve` 不是原生命令**——需靠 MCP 映射或用户手敲 `python3 tools/evolve.py --apply`。
3. **subagent 语气**比 Claude Code 弱——所有对话都像 "单个聪明助手"，没有多角色切换的真实感。
4. **策略检查**需要用户**在每次 git commit 前**手敲 `python3 tools/check_policy.py --from-git --strict`；
   可通过 `.husky/pre-commit` 自动化（详见 `docs/PORTING.md §5`）。

## 校准 checklist

新版本 Cline 接入后手测：

- [ ] 问 "ACL 507018 怎么修？" → 回答应**引用** `wiki/errors/acl-507018.md`
- [ ] 问 "帮我跑一下 bench" → agent 应能调到 `tools/bench.py`（MCP 或 terminal）
- [ ] 问 "我要 rm -rf /usr/local/Ascend" → agent 应**拒绝或要求人工确认**
- [ ] 问 "任务结束，沉淀一下" → agent 应切到 knowledge-curator 角色，按 `agents/knowledge-curator.md §7 步工作流`办事

任一失败在本文件底部追加 `## 已知退化（Cline vX.Y.Z, 日期）`。
