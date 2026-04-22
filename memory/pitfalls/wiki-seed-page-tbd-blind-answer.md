---
id: wiki-seed-page-tbd-blind-answer
kind: pitfall
tags: [bootstrap, wiki, confidence, seed-page]
source: case/2026-04-20-porting-selfcheck
created_at: 2026-04-20
verified_at: 2026-04-20
confidence: high
ttl_days: 365
related_wiki: [910b, 310p, cann, mindie]
---

## 坑
Wiki 种子页（如 `wiki/hardware/910b.md`、`wiki/software/cann.md`）的"规格 / 版本矩阵"段
初始带 `TBD`。如果主 agent 只按 `related:` 命中就注入整页给自己，容易在回答里直接照搬
"TBD"或者用训练记忆补上去而不标注来源，**制造看起来权威但未经验证的答案**。

## 规避
1. 主 agent 遇到 wiki 页 frontmatter `status: draft` 或段内含 `TBD` 时：
   - 在回答开头**显式标注 "low confidence"** 并给出验证命令
   - **不**把 TBD 字段当成 "0 / 无 / 不存在" 的等价语义
2. Curator 在 consolidation 时扫 `TBD` 并把受影响页列在 `docs/EVOLUTION-STATS.md` 的
   "seed-gap" 小节，督促人工补齐。
3. 为每个 status=draft 的 wiki 页在 `memory/facts/` 或用户 session 里挂一个"待验证"
   书签，填完后移除。

## 首次观察
cases/2026-04-20-porting-selfcheck.md · Step 2：被问"910B 有多少 AICore？"时
910b.md 仅有 `TBD`，agent 正确识别并降级诚实回答。
