# 知识模型 (Knowledge Model)

> 定义 ascend-forge 中五种知识载体的 schema、文件布局、与索引规则。
> 任何新载体必须先在此登记。

---

## 1. 总览

```
memory/     原子 · 横切 · 快查        （facts / lessons / pitfalls / preferences）
skills/     过程 · SOP · 可触发        （一目录一 skill，SKILL.md + 脚本）
wiki/       实体 · 纵深 · 可互链      （一实体一页，Karpathy-style）
cases/      事件 · 叙事 · 可检索      （一次任务一份归档）
rules/      启发 · 全局 · 可审核      （proposals → ACTIVE → archive）
```

相互关系：

```
cases  ──抽取──▶  memory / wiki / skill / rule-proposal
memory ──聚合──▶  wiki (纵深补齐)
memory ──升格──▶  rule (重复模式)
skill  ──失败──▶  pitfall (失败案例回流)
wiki   ──索引──▶  memory / cases / skill  (反向链接)
```

---

## 2. memory/

### 2.1 分类

| 目录 | 语义 | 典型例子 |
|---|---|---|
| `facts/` | 可验证的单句事实 | "CANN 8.0.0 默认禁用融合算子 xxx" |
| `lessons/` | 任务复盘的短文 | "适配 Qwen2 MoE 时 router 精度要单独对齐" |
| `pitfalls/` | 坑 + 规避方案 | "MindIE 启动报 ACL_ERROR 500002 → 检查 kv_cache 配置" |
| `preferences/` | 用户偏好 | "优先 W8A8，次选 W4A16" |

### 2.2 文件 schema

文件名：`memory/<category>/<kebab-id>.md`，与 frontmatter `id` 一致。

必填 frontmatter：`id, kind, tags, source, created_at, confidence`。

```markdown
---
id: cann-800-fused-op-default-off
kind: fact
tags: [cann, operator, fusion, "v8.0.0"]
source: case/2026-04-18-qwen2-adapt
created_at: 2026-04-18
verified_at: 2026-04-18
confidence: high
ttl_days: 180
related_wiki: [cann, operator-fusion]
---

CANN 8.0.0 默认关闭若干融合算子（见官方 release note #xxx），启用需
`export ASCEND_OP_FUSION_ON=1`。该默认值在 7.x 是开启。
```

### 2.3 索引

`memory/INDEX.md` 人读，自动追加。`memory/INDEX.jsonl` 可选机读。

---

## 3. skills/

### 3.1 目录约定

```
skills/<slug>/
  SKILL.md              必须
  scripts/              可选（可执行脚本）
  templates/            可选（配置模板）
  examples/             可选（示例命令/输入输出）
```

### 3.2 SKILL.md schema

```markdown
---
name: mindie-deployment
description: 用 MindIE 把一个 HF 模型在 910B 上拉起推理服务
trigger:
  - "mindie"
  - "部署 LLM"
  - "推理服务"
applies_to:
  hardware: [910B, 310P]
  software: [CANN>=7.0, MindIE>=1.0]
version: 0.1.0
owners: [ascend-deployer]
safety: read-write          # read-only | read-write | dangerous
---

# <Skill 名称>

## 何时使用
## 前置条件
## 步骤
## 验证
## 失败回流（失败时在此 skill 下 append 失败案例链接）
## 参考
```

### 3.3 触发语义

- `trigger` 是**或**关系，任一命中即候选。
- Router 在多 skill 命中时，按 `owners` 匹配当前 subagent > `version` 新 > `examples/` 更多排序。

---

## 4. wiki/

### 4.1 kinds（每种一套模板）

| kind | 放在 | 例子 |
|---|---|---|
| `hardware` | `wiki/hardware/` | 910b, 310p, atlas-800 |
| `software` | `wiki/software/` | cann, mindie, mindspore, torch-npu, vllm-ascend |
| `model` | `wiki/models/` | qwen2-72b, deepseek-v3, llama3-70b |
| `operator` | `wiki/operators/` | flash-attention, rotary-embedding, rms-norm |
| `error` | `wiki/errors/` | acl-500002, e39999, aicore-pipe |
| `playbook` | `wiki/playbooks/` | first-time-adapt, perf-regression-diagnosis |

### 4.2 通用 frontmatter

```yaml
---
id: qwen2-72b
title: Qwen2-72B
kind: model
aliases: ["Qwen2 72B", "qwen2:72b"]
tags: [llm, dense, chinese]
related: [qwen2-7b, mindie, flash-attention]
status: stable
last_verified: 2026-04-20
sources:
  - https://hf.co/Qwen/Qwen2-72B
  - https://www.hiascend.com/...
---
```

### 4.3 模板片段

每 kind 的骨架见 [`wiki/INDEX.md`](../wiki/INDEX.md) 与各分区示例页。

### 4.4 双向链接

`related:` 是作者写；`## Backlinks` 由 `tools/wiki_link_check.py` 维护。

---

## 5. cases/

### 5.1 命名

`cases/YYYY-MM-DD-<kebab-slug>.md`，一天内同 slug 追加 `-2`、`-3`。

### 5.2 schema

```markdown
---
id: 2026-04-20-qwen2-72b-oom
date: 2026-04-20
duration_min: 42
subagents: [ascend-diagnoser, ascend-deployer]
models: [qwen2-72b]
hardware: [910b]
software: [mindie-1.0]
outcome: resolved             # resolved|partial|blocked|abandoned
tags: [oom, kvcache, inference]
extracted:
  memory: [pitfall-acl-500002-qwen2]
  wiki: [models/qwen2-72b, errors/acl-500002]
  rules: [check-kvcache-before-oom]
---

## 问题
## 过程（时间线）
## 根因
## 修复
## 复盘（可以做得更好的）
## Metrics
```

### 5.3 索引

`cases/INDEX.jsonl`（每行一个 case 的 frontmatter 精要），可供 BM25/向量检索。

---

## 6. rules/

### 6.1 目录

```
rules/
  ACTIVE.md           生效中的规则，全量加载进 planner，**不要长**
  proposals/          pending
  archive/            已退役 / 被取代
```

### 6.2 rule 条目 schema

见 [`EVOLUTION.md §4.4`](EVOLUTION.md#44-rule-proposal)。

### 6.3 ACTIVE.md 格式

```markdown
# Active Rules

> 最后更新：2026-04-20

## Planning
- **R001** 开始任何诊断前，先 `msprof --version` 与 `npu-smi info` 打底线。
  *evidence: 3 cases · since 2026-03-01*

## Writing code
- **R014** 算子替换必须同时加精度对齐脚本，否则拒绝提交。

## Safety
- **R020** 永不自动 `rm` 驱动目录；需要时生成命令给用户确认。
```

规则 ID 全局唯一（R001, R002 …），archive 不复用。

---

## 7. 索引系统

| 索引 | 文件 | 维护者 | 形态 |
|---|---|---|---|
| memory 索引 | `memory/INDEX.md` | consolidation | 手读 + 机读 |
| wiki 人读索引 | `wiki/INDEX.md` | consolidation | 目录 + 摘要 |
| wiki 机读索引 | `wiki/INDEX.jsonl` | `tools/wiki_link_check.py` | 一行一页 |
| cases 索引 | `cases/INDEX.jsonl` | `tools/rag_index.py` | 一行一 case |
| skills 索引 | `skills/INDEX.md` | consolidation | trigger → skill 映射表 |

---

## 8. ID 命名约定

- **kebab-case**，`[a-z0-9-]+`，不含路径分隔符。
- 形如 `<kind>-<subject>-<qualifier>`：`pitfall-acl-500002-qwen2`、`fact-cann-800-fused-op-default-off`。
- rules 用 `R<4 位数>`。
- cases 用 `YYYY-MM-DD-<slug>`。
- wiki id 最窄且稳定（`qwen2-72b` 而不是 `qwen2-72b-on-910b`）。

---

## 9. 校验清单（每次 consolidation 应通过）

- [ ] 所有 `source:` 指向的 case 都存在
- [ ] wiki 每页都有 `last_verified`
- [ ] wiki `related:` 目标都存在，无孤链
- [ ] memory `ttl_days` 超期的标了 `stale`
- [ ] rules ACTIVE 没有 id 冲突 / 废弃引用
- [ ] skills trigger 无歧义（两个 skill 不能 100% 同触发词）
- [ ] 索引和目录内容对齐
