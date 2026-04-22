# Adapter · Cursor

> Cursor（cursor.sh）是一个 VSCode fork 的 AI IDE。本 adapter 说明如何把 Ascend-Forge
> 的知识库和行为约束**尽量完整**地映射到 Cursor 的 `.cursor/rules/` + `@Docs` 机制。

## 认知差异（与 Claude Code 对比）

| 维度 | Claude Code | Cursor |
|-----|------------|-------|
| 入口文件 | `CLAUDE.md` | `.cursor/rules/*.mdc`（替代了老版 `.cursorrules`） |
| 子 agent | 原生支持 `@agent-name` | **无**（只有单主 agent + Composer/Chat/Cmd-K 三种交互模式） |
| 工具调用 | Bash/Read/Write/Edit/Glob/Grep | Cursor 内置 terminal / file tools + MCP（需自配） |
| 规则热加载 | 主 agent 自动读 rules/ACTIVE.md | `.cursor/rules/*.mdc` 按 `globs:` 字段按需加载 |
| Skill 系统 | `skills/<name>/SKILL.md` 按 trigger 加载 | 无原生；用 @Docs 引用手工触发 |

## 集成步骤

### 1. 创建 `.cursor/rules/ascend-forge.mdc`

把 `rules/ACTIVE.md` 的内容复制进来，frontmatter 设为全局：

```yaml
---
description: Ascend-Forge 全局行为约束
globs: ["**/*"]
alwaysApply: true
---
```

### 2. 子 agent 降级策略（无原生支持）

Cursor 没有 `@ascend-diagnoser` 这种多 agent；我们用**规则文件 + 前缀指令**模拟：

- 为每个 subagent 创建一个独立 `.cursor/rules/<name>.mdc`，`globs:` 设成该角色
  最常碰的文件模式：
  - `ascend-adapter.mdc` → `globs: ["**/*.py", "wiki/models/**", "wiki/operators/**"]`
  - `ascend-deployer.mdc` → `globs: ["**/serve*.py", "**/launch*.sh", "wiki/software/mindie.md", "wiki/software/vllm-ascend.md"]`
  - `ascend-diagnoser.mdc` → `globs: ["wiki/errors/**", "**/*.log"]`
  - `ascend-env-doctor.mdc` → `globs: ["wiki/hardware/**", "wiki/software/cann.md", "**/Dockerfile*"]`
  - `ascend-tuner.mdc` → `globs: ["**/*.py"]` + 一条 `@Cmd-K` 触发词 `调优` 才激活
  - `ascend-benchmarker.mdc` → `globs: ["bench/**", "**/benchmark*.py"]`
- 每个 .mdc 的正文就是对应 `agents/<name>.md` 的 prompt 段，去掉 `tools:` frontmatter。

### 3. 知识库 @Docs 映射

把 `wiki/` 整个目录加到 Cursor 的 @Docs，让聊天里能 `@wiki/errors/acl-507018` 直接引用。
步骤（Cursor 0.40+）：

1. `Cmd-Shift-P` → "Add new doc"
2. 选 `Indexed docs` → 指向 `wiki/`
3. 重启 Cursor 的 indexer

### 4. 工具（MCP）

Ascend-Forge 用到的外部工具（npu-smi / msprof / git）在 Cursor 里走 **terminal**。
若要做**自动化 consolidation**（类似 Claude Code 里的 `/evolve`）：

- 方案 A（推荐）：外部 cron 跑 `python3 tools/evolve.py --apply`，Cursor 只负责交互。
- 方案 B：装 MCP shell server，在 agent session 内调用。成本高、风险更大。

## 已知限制

1. **无真子 agent**。Cursor 1 agent + rules hack 的组合，语义隔离弱于 Claude Code。
   体感：`@ascend-diagnoser` 语气 vs. `@ascend-tuner` 语气 的区分会被模糊。
2. **skill 系统缺失**。`skills/ascend-troubleshoot/SKILL.md` 这种按 trigger 加载的能力在
   Cursor 里只能靠 **手工粘贴** 或 **@Docs 引用**；自动加载做不到。
3. **策略检查非强制**。`.agent/evolution_policy.md` 只能作为 prompt 提示；
   没有 `tools/check_policy.py --from-git` 的 pre-commit 自动化前，规则是"软约束"。
   强烈建议把 `tools/check_policy.py` 挂到 `.husky/pre-commit`（见 `docs/PORTING.md §5`）。
4. **consolidation 触发**。没有自动 "task 结束钩子"，靠用户手动敲 `/evolve` 或在
   `.cursorrules` 里写"每次收尾必建议运行 evolve.py"的软提示。

## 校准 checklist

移植到新 Cursor 版本后（例如 0.50+），以下场景应该手测一遍：

- [ ] 打开 `wiki/errors/acl-507018.md`，问"按这页修我的代码"——主 agent 应能读到该页
- [ ] 打开 `bench/golden-questions.yaml`，问"跑 bench 并汇报"——应执行 `tools/bench.py`
- [ ] 打开 `rules/ACTIVE.md`，问"你遵守这里的哪条？"——agent 列出的条数应 > 0
- [ ] 问"你是 ascend-diagnoser 吗？"——若启用了 `ascend-diagnoser.mdc` 应回 "是"

失败了就在本文件底部追加 `## 已知退化（YYYY-MM-DD）` 小节，记下 Cursor 版本 + 失败点。
