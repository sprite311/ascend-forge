---
id: case-must-produce-skill-or-skip-reason
date: 2026-04-22
status: pending
kind: rule_proposal
tier: R
proposed_number: R034
evidence:
  - case/2026-04-22-wave8 (Wave 8 close · 小组目标对齐)
  - lesson/lesson-architecture-critique #11 (L4 层空)
source: case/2026-04-22-wave8
---

# 提案：R034 —— `outcome=resolved` 的 case 必须声明 skill_status

## 问题陈述

小组定义的平台目标（Wave 8 收到）：
> "通过任务总结沉淀复盘案例，**形成可复制的方案/脚本**"、"5 天 → 0-1 天"。

当前架构里 "skills/" 层是空的——`memory/lessons/lesson-architecture-critique.md` #11 已识别这是**最大方向性缺口**。

根因之一：R031 说"每任务最多 1 skill"（**上限**），但没说"至少要决策一次"。结果就是**每次都不写**，因为写 SKILL.md 成本高于不写。

## 提案

给 `rules/ACTIVE.md` 加 R034：

```
R034 · Case 必须声明 skill 产出或 skip 理由
    一份 outcome: resolved 的 case，其 Curator Log 必须包含一条
    skill_status: 字段，取值：
      · created: skills/<slug>/  —— 本次任务沉淀出新 skill（含 SKILL.md）
      · updated: skills/<slug>/  —— 本次补充已有 skill（追加小节 + source）
      · skipped_because: <原因>   —— 明确决策不沉淀，给原因
    目的：强制 curator 在"沉淀 / 不沉淀"之间做**显式**判断，
    避免 L4 程序记忆层长期空置。
    不沉淀的合法原因（示例）：
      · "纯 tools 重构，没对应客户任务可抽"
      · "已在 skills/<X>/SKILL.md 里有重合覆盖，跳过"
      · "单次偶发问题，没复用价值"
```

## 为什么是 rule 不是"建议"

小组目标把"产出脚本"作为**成功标准**，不是"最佳实践"。软承诺（"curator 可以写 skill"）已经证明不工作了——骨架 Wave 1-7 做完，skills/ 还是 0。改硬约束是合理升级。

## 与现有规则的关系

- **R031**："每任务最多 1 skill" —— 限制**上限**；R034 限制**下限**（强制决策，不强制产出）。两者互补。
- **R011**："只追加，不覆盖" —— 不冲突；skill 的 `updated:` 形态天然是追加。
- **R021**（写白名单含 `skills/`）—— 已允许写 skills/，R034 只是在 curator 语义层加约束。

## 验收方式

三个月试跑期后看：
1. `skills/*/` 目录数 ≥ 6（第一批候选见 lesson-architecture-critique #11 建议）；
2. `cases/*.md` 中 `skill_status: skipped_because` 出现的频次 ≤ 50%（若 > 50% 说明规则摆设，要反思为什么还是不沉淀）；
3. 至少 1 个 skill 被**场景 2 反向复现**（客户现场用，带 `reproduced_on_sites: >0`）。

## Evidence（暂 2 条，差 1 条就 auto-promote）

- **Evidence #1**：`cases/2026-04-22-wave8.md` —— 小组目标原文 + 架构 gap 分析。
- **Evidence #2**：`memory/lessons/lesson-architecture-critique.md` #11 —— L4 层空的量化清单（skills: 0）。

达到 3 条 evidence 后，按 R032 auto-promote。第 3 条 evidence 应来自：**下一次真实任务没用 R034**（产生"本应强制但没强制"的事实），证明规则需要兑现。

## 风险

- **形式主义风险**：curator 为了合规写"skipped_because: 无"。缓解：每 10 次 skipped_because 做一次抽样审查，看原因是否真实、是否该其实 created。
- **骨架期 noise**：bootstrap commits 可能批量生成 case，R034 会把"抽一次 lesson" 这种工具性 case 也套上。缓解：bootstrap commit 豁免（check_policy.py 已有 `--from-git` 和人工 case 的区分机制，见 R031 当前执行）。
