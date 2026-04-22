# Active Rules

> **最后更新**：2026-04-20
> **只被 planner 全量加载**——请保持简短，每条 ≤ 2 行。
> **不要**直接在此文件新增规则；走 `proposals/` → promote。

---

## Planning

- **R001** 开场必读 `rules/ACTIVE.md` + 索引（memory、wiki）；按意图命中才按需加载具体页。
  *evidence: bootstrap · since 2026-04-20*

- **R002** 涉及昇腾域问题 → 路由到对应 subagent，不自己闷头答。
  *evidence: bootstrap · since 2026-04-20*

## Knowledge hygiene

- **R010** 任何 memory / wiki / skill / rule 写入必须带 `source:`（case/user-confirmed/official-doc）。
  *evidence: bootstrap · since 2026-04-20*

- **R011** Wiki 禁整页重写；只追加带日期小节 + Changelog 一行。
  *evidence: bootstrap · since 2026-04-20*

- **R012** 冲突事实不静默覆盖；两方保留 + 生成 proposal。
  *evidence: bootstrap · since 2026-04-20*

## Safety

- **R020** 破坏性命令（`rm -rf` / `dd` / 驱动覆盖 / `modprobe` / `rmmod` / 写 `/dev/`）**不自动执行**，打印给用户确认。
  *evidence: bootstrap · since 2026-04-20*

- **R021** 写入路径受 `.agent/config.yaml` 的 `write_whitelist` 约束；不写 `docs/`、`.agent/`、`adapters/`、根级说明文件。
  *evidence: bootstrap · since 2026-04-20*

## Evolution

- **R030** 任务结束必须调用 `knowledge-curator`（闲聊除外）。
  *evidence: bootstrap · since 2026-04-20*

- **R031** 单任务产出上限：3 memory / 1 skill / 1 rule proposal / 无限 wiki 追加 / 1 case。
  *evidence: bootstrap · since 2026-04-20*

- **R032** Rule 晋升：需用户 `/rules promote` 或 ≥ 3 独立 case 证据；被取代的 rule 移 `archive/`，ID 不复用。
  *evidence: bootstrap · since 2026-04-20*

- **R033** 命中 `status: draft` 或含 `TBD` 的 wiki 页时，回答必须：(1) 首行 `⚠️ 低置信度` 标注 (2) 给验证命令 (3) 不把猜测值写入 `memory/facts/`。
  *evidence: 3 cases · promoted from `seed-critical-wiki-before-first-use` · since 2026-04-21*

---

## 说明
- ID 规则：`R<4 位数>`，全局唯一，移除后**不复用**。
- Archive：被取代 / 失效规则移入 `rules/archive/<id>.md` 留档。
- 本文件由 consolidation 与 user-approved proposals 共同维护；不手改。
