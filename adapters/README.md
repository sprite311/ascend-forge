# Adapters · 把 Ascend-Forge 跑到不同 agent 环境上

本目录存放各运行时的**移植指南**。Ascend-Forge 的母体是 Claude Code，但知识库
（`memory/` / `wiki/` / `cases/` / `rules/` / `skills/`）和工具（`tools/*.py`）是
**运行时无关**的——任何支持"读文件 + 跑命令 + 维持会话上下文"的 agent 都能用。

## 已覆盖

| 运行时 | 状态 | 入口文件映射 | 子 agent 支持 | 说明 |
|-------|-----|-------------|---------------|-----|
| [Claude Code](claude-code/README.md) | ✅ 原生 | `CLAUDE.md` | 原生 `@name` | 母体；0 改动即用 |
| [openclaw](openclaw/README.md) | ⚠️ 需按版本核实 | `AGENTS.md` | persona chain | 工具名待维护 |
| [Cursor](cursor/README.md) | ⚠️ 降级 | `.cursor/rules/*.mdc` | **无**（规则文件 + globs 近似） | 无真子 agent |
| [Cline](cline/README.md) | ⚠️ 降级 | `.clinerules/` | **无**（角色 prompt 切换） | MCP 可接工具 |

## 能力等级

不是所有运行时都能跑满 Ascend-Forge 的全部能力。按**能力下降**排序：

```
                           Claude Code (100%)
                                  │
              ┌───────────────────┼───────────────────┐
         openclaw (~85%)      Cursor (~70%)       Cline (~75%)
              │                   │                   │
        工具名要对齐        无子 agent          无子 agent
        persona chain 可用   rules/globs 近似   .clinerules 统一载入
        skill 靠手动         @Docs 引 wiki      MCP 可接工具
```

### 哪些能力在降级运行时**必然丢失**

1. **真子 agent 语气分化**——只有 Claude Code / openclaw 有；Cursor / Cline 里
   所有回答都是"单个助手"，`@ascend-diagnoser` vs `@ascend-tuner` 的体感区别会被模糊。
2. **skill 按 trigger 自动加载**——只有 Claude Code 原生支持；其它运行时要用户手动引用。
3. **curator 任务钩子**（"任务结束自动调 curator"）——目前只有 Claude Code 支持；
   其它环境要用户敲 `/evolve` 或 MCP 触发。

### 哪些能力**完全不丢**

知识库本身（所有 md / jsonl 文件）+ 自动化工具（`tools/*.py`）跨运行时 100% 一致。
最坏情况下你总能用：

```bash
python3 tools/evolve.py --apply   # consolidation
python3 tools/bench.py            # 路由回归
python3 tools/curate.py --trace trace.md  # 候选抽取
```

## 选型建议

- **用昇腾做项目、团队在 VSCode**：Cline（MCP + rules 齐活，子 agent 丢得可接受）
- **用昇腾做产品、要多人协作**：Claude Code（子 agent 语气 + 原生 skill 效率最高）
- **个人摸索 + 代码为主**：Cursor（.mdc 按 globs 激活最自然）
- **已用 openclaw**：跟随现有栈即可，参考 openclaw/ 目录

## 新增运行时的步骤

1. 建目录 `adapters/<runtime>/`
2. 照 `cursor/README.md` 结构写 4 节：认知差异 / 集成步骤 / 已知限制 / 校准 checklist
3. 跑 `python3 tools/bench.py --strict` 验证路由回归仍 ≥ 90%
4. 在本文件表格加一行
5. 写一条 case `cases/YYYY-MM-DD-porting-<runtime>.md` 记录本次移植的坑
