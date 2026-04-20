# Evolution Policy — 进化护栏

> 这是 `knowledge-curator` 及主 agent 在"写入长期知识"时必须遵守的硬约束。
> 违反任一项视为 bug。

---

## 1. 白名单写入

只允许写：

- `memory/**`
- `skills/**`
- `wiki/**`
- `cases/**`
- `rules/proposals/**`

**拒绝写**：

- `rules/ACTIVE.md`
- `rules/archive/**`
- `docs/**`
- `.agent/**`
- `adapters/**`
- `CLAUDE.md` / `AGENTS.md` / `README.md`（根级说明）

## 2. 每条写入必须带 `source:`

- `source: case/<case-id>`
- `source: user-confirmed`
- `source: official-doc:<url>`

三类之外一律拒绝。

## 3. 单任务产出上限

- `memory/` 新条目 ≤ 3
- `skills/` 新 skill ≤ 1（修改现有不限）
- `rules/proposals/` 新提案 ≤ 1
- `wiki/` 追加不限（但每次是"追加小节"，不是"整页重写"）
- `cases/` 固定 1 条（这一次任务）

## 4. 冲突策略

检测："已有事实 F 与新事实 F' 明显矛盾"。
动作：**两者都保留**（已有保留，新建 `*-conflict-<date>.md`），同时生成一条 rule proposal 请求裁决。**严禁静默覆盖**。

## 5. Rule 生命周期

- Agent 只能写 `rules/proposals/`
- Promotion 到 `rules/ACTIVE.md`：
  - 用户显式 `/rules promote <id>`；或
  - 证据数 ≥ `rule_promotion.min_evidence`（默认 3）且无冲突 → 自动晋升（但仍记一条审计日志）
- ACTIVE 里移除的 rule 移到 `rules/archive/`，ID 不复用。

## 6. 破坏性命令

匹配以下 pattern 即**不自动执行**，改成"打印命令请用户确认"：

- `rm -rf`
- `dd if=`
- `mkfs.*`
- `modprobe` / `rmmod`
- `> /dev/`
- 驱动 / 固件覆盖、`insmod`、`npu-smi ... -o reset` 之类

## 7. 幻觉防线

- `confidence: low` 的条目**不**自动进 memory/facts，改进 `rules/proposals/` 或 case 的 "待验证" 小节。
- 若依据是 "模型训练记忆"（没有 case 或 doc 源）→ 禁止写入。

## 8. Consolidation 原子性

`tools/evolve.py` 跑 consolidation 前：

1. `git status` 确认工作区干净（或仅有 cases/）
2. 建工作分支 `consolidation/<timestamp>`
3. 全部变更完成后一次 commit
4. 任一步失败则 `git restore -SW` 并告警

## 9. 审计

所有进化动作在 case 末尾的 `## Curator Log` 里留痕：

```
- wrote: memory/pitfalls/acl-500002-qwen2.md
- appended: wiki/models/qwen2-72b.md #已知-OOM-场景
- proposed: rules/proposals/2026-04-20-check-kvcache-before-oom.md
```

这样 `git diff` 就是完整的知识变更记录。
