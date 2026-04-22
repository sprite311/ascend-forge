---
id: lesson-seed-page-must-link-errors
kind: lesson
tags: [wiki, content-design, karpathy-wiki, cross-link, curator]
source: case/2026-04-20-troubleshoot-migration-wave1
created_at: 2026-04-20
verified_at: 2026-04-20
confidence: high
ttl_days: 365
related_wiki: [cann, 910b]
---

## 教训
**软件 / 硬件种子页必须反向链接到 `wiki/errors/` 的高频条目。**
只填"规格 / 矩阵 / 安装"是不够的——用户大多数提问路径是 "报错 → 找修复"，
而不是 "看规格 → 问 how-to"。

## 具体做法
在 `wiki/software/<x>.md` 和 `wiki/hardware/<x>.md` 的 `## 常见坑` 小节列出指向
`wiki/errors/*.md` 的**命中清单**（按频次排序，每条一行：签名 / 短描述 / 链接）。

## 反例
Wave 0 cann.md 只有 "_尚未记录。由 `ascend-env-doctor` 按场景追加。_"——
导致用户问 `npu-smi info 无输出` 时，agent 从 cann.md 找不到 jump-off，
只能走训练记忆回答；这正是 `pitfall-wiki-seed-page-tbd-blind-answer` 描述的坑。

## 正例
Wave 1 cann.md `## 常见坑` 小节手写了 4 条 `wiki/errors/` 链接；
同时 9 个新建 errors 页的 `related:` 字段都包含 cann/软件主页，
`wiki_link_check.py` 自动补出 `## Backlinks`，闭环。

## 适用范围
- 所有 `kind: software | hardware | model` 的 wiki 页
- 首次创建时由主 agent 填；后续由 curator 在 consolidation 时扫 errors/ 新增项并追加
