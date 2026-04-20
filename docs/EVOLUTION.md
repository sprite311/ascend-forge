# 进化循环 (Evolution Loop) 详细规范

> 本文是 [`ARCHITECTURE.md §4`](ARCHITECTURE.md#4-进化循环evolution-loop) 的详细展开。
> 读者：`knowledge-curator` subagent 与想改 curator 行为的人。

---

## 1. 核心不变量 (Invariants)

1. **没有"默记"**：任何进入长期知识的条目都必须能指回**来源 case**（或 `user-confirmed`）。
2. **没有"覆盖"**：事实冲突时永远新增 + 走 proposal，而非静默改写。
3. **没有"孤岛"**：每条新知识必须至少和 1 个现存实体关联（加 link 或 tag）。
4. **没有"爆炸"**：单任务输出上限 — 3 memory / 1 skill / 1 rule proposal / 任意数量 wiki 追加。
5. **没有"失忆"**：每次 consolidation 前先 `git commit`，任何合并都可回滚。

---

## 2. 数据流状态机

```
           ┌──────────────┐
           │  task running │
           └──────┬───────┘
                  │ task end
                  ▼
           ┌──────────────┐
           │  case written │  ← 始终产出，一条不漏
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │  extract     │  curator 扫 case，列候选
           └──────┬───────┘
                  │
          ┌───────┼────────┬──────────────┬───────────────┐
          ▼       ▼        ▼              ▼               ▼
        memory  skill   wiki-patch   rule-proposal     drop
        (直写)  (直写)   (直写追加)   (→ proposals/)   (忽略)
                  │
                  └── 周期 consolidation ──┐
                                          ▼
                          ┌──────────────────────┐
                          │ dedupe / merge / gc  │
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │ index rebuild        │
                          └──────────┬───────────┘
                                     ▼
                              Git commit
```

---

## 3. 候选分类器 (Classify)

curator 收到一条候选知识后，按如下顺序判定：

| 候选特征 | 载体 |
|---|---|
| 用户明确说 "记住 / 以后都 / 我偏好" | `memory/preferences/` |
| 可验证的单句事实（版本号、官方默认值、阈值） | `memory/facts/` |
| 报错签名 + 规避 | `memory/pitfalls/` + `wiki/errors/` 双写 |
| 任务复盘的"这次学到了什么" | `memory/lessons/` |
| 对**某个实体**的认知增量（模型/算子/软件/硬件/playbook） | `wiki/<kind>/<id>.md` |
| 一套可重复的步骤（被至少执行 2 次） | `skills/<slug>/SKILL.md` |
| 决策启发式（"遇到 X 应该先 Y"） | `rules/proposals/` |

> 候选可以**命中多项**——同一条信息出现在 memory + wiki 是刻意的冗余，检索路径不同。

---

## 4. 写入契约

### 4.1 memory 原子条目

文件名：`memory/<category>/<kebab-slug>.md`

```markdown
---
id: pref-quant-w8a8
kind: preference            # fact|lesson|pitfall|preference
tags: [quantization, inference]
source: case/2026-04-20-qwen2-72b-oom
created_at: 2026-04-20
verified_at: 2026-04-20
confidence: high            # low|medium|high
---

用户偏好 W8A8 量化方案优先于 W4A16（除非显存强约束）。
```

### 4.2 skill

目录：`skills/<slug>/SKILL.md`，可选 `scripts/` 子目录放脚本。

```markdown
---
name: mindie-deployment
trigger:
  - "mindie"
  - "部署"
  - "推理服务"
applies_to: [910B, 310P]
version: 0.1.0
---

# MindIE 部署 SOP

## 前置
## 步骤
## 验证
## 常见坑 → wiki/errors/*
```

### 4.3 wiki 追加

**不要覆盖整页**。在相应小节下以 `### YYYY-MM-DD 追加：<简述>` 开头追加一节，并在页尾 `## Changelog` 记一行：

```
- 2026-04-20: 追加 OOM-with-kvcache 场景，来源 case/2026-04-20-qwen2-72b-oom
```

### 4.4 rule proposal

`rules/proposals/<date>-<slug>.md`：

```markdown
---
id: check-kvcache-before-oom
proposed_at: 2026-04-20
evidence:
  - case/2026-04-20-qwen2-72b-oom
  - case/2026-04-18-llama3-oom
status: pending             # pending|accepted|rejected|superseded
---

## 规则
OOM 诊断时，必须**先**检查 `kv_cache_block_size` × `max_num_seqs` 的估算显存，
再看模型权重。

## 理由
...

## 生效范围
ascend-deployer, ascend-diagnoser
```

Promotion 条件：
- 用户 `/rules promote <id>`；或
- 证据数 ≥ 3 且无冲突；
被接受的 rule 复制到 `rules/ACTIVE.md`，proposal 标记 `accepted` 归档到 `rules/archive/`。

---

## 5. Consolidation（周期合并）

执行时机：
- 每日（如果跑了调度）
- 每 10 个新 case
- 用户 `/consolidate`

步骤（由 `tools/evolve.py` 或人工触发 curator）：

1. **dedupe**：相同 `id` 或近似条目合并（近似判定：标题相似度 + tag 交集）。
2. **conflict**：新旧事实矛盾 → 生成 proposal + 保留两方。
3. **GC**：`verified_at` 超过 `ttl`（默认 180 天）且没被引用 → 标 `stale`，不删。
4. **backlink**：扫 wiki `related:` frontmatter，双向补齐。
5. **index rebuild**：
   - `wiki/INDEX.md`（人读）+ `wiki/INDEX.jsonl`（机读）
   - `memory/INDEX.md`
   - `cases/INDEX.jsonl`（含 embedding 字段，可选）
6. **Git commit**，消息模板：
   ```
   consolidate: +N memory / +M wiki / +K proposals / gc S stale
   ```

---

## 6. 检索 (Retrieve)

每次任务启动，主 agent 的"开场动作"：

1. 读 `rules/ACTIVE.md`（短文，全量）。
2. 用用户问题的关键词 + 识别出的实体，查：
   - `memory/INDEX.md` → 命中的原子条目
   - `wiki/INDEX.jsonl` → 命中的实体页
   - `cases/INDEX.jsonl` → TopK 语义相似案例
   - `skills/` → trigger 命中
3. 只**注入被命中的部分**进上下文，不要全量塞。
4. 在思考中显式引用来源（"依据 `wiki/models/qwen2-72b.md#已知-oom-场景`"），让后续 curator 能追踪。

---

## 7. 失败模式与抗性

| 失败模式 | 表现 | 缓解 |
|---|---|---|
| 噪声爆炸 | Curator 生成大量废条目 | 速率限制 + 证据要求 + 人工 promotion |
| 幻觉写入 | 不存在的事实被记住 | 必须带 source；低 confidence 进 proposals |
| 过拟合用户 | 把一次偏好泛化成全局规则 | preferences 只记个人，rules 要 ≥ 2 次证据 |
| 循环引用 | A 说 "见 B"，B 说 "见 A" | wiki link checker 检测 |
| 索引漂移 | 文件改了索引没更新 | consolidation 强制重建；CI 可加 check |
| 平台跑偏 | Claude Code 能跑 openclaw 不能 | 所有工具调用走 `adapters/*/tools.md` 的抽象 |

---

## 8. 可观测性

建议（非强制）：
- `cases/` 下每个 case 尾部加 `## Metrics`：任务耗时、工具调用数、失败重试数。
- `tools/evolve.py` 输出 `docs/EVOLUTION-STATS.md`：memory/wiki/skill/case 的数量随时间变化。
- 每次 consolidation 一次 commit，`git log --oneline` 就是进化日志。
