---
id: 2026-04-20-draft-wiki-flash-attention
date: 2026-04-20
tags: [draft-wiki, flash-attention, operators, rule-evidence, seed-critical-wiki-before-first-use]
models: []
hardware: [910b]
software: [torch-npu]
outcome: resolved
---

# 用户问 flash-attention 在昇腾上的算子替换时，agent 正确降权了

## 用户问题

> torch_npu 上有没有 flash-attention？性能如何？

## agent 行为

命中 `wiki/operators/flash-attention.md`。frontmatter `status: draft` + 正文 4 个 `TBD`。
按 `rules/proposals/seed-critical-wiki-before-first-use` 规定：

```
⚠️ 低置信度：wiki/operators/flash-attention.md 当前 status=draft 且含 4 处 TBD，
以下回答基于训练记忆，未经验证。

（概览，以下需核实）
- torch_npu 自 2.1.x 起提供 `torch_npu.npu_fusion_attention`，是昇腾 ATB 的
  Flash-Attention 融合算子封装。接口兼容 HuggingFace 的 scaled_dot_product_attention。
- 性能相对 naive MHA 理论上应 2-4× 加速（GPU 典型值，昇腾上数据待真机 benchmark）。
- 精度：与 GPU FA2 应在 1e-3 以内，具体需对齐测试。

核实步骤：
  1. 在你的机器上 `python -c "import torch_npu; help(torch_npu.npu_fusion_attention)"`
  2. 用 wiki/playbooks/general-debug.md §精度对齐段 的方案对比 GPU / NPU 输出
  3. 结果回填到 wiki/operators/flash-attention.md 的"追加回执"段
```

不新增 memory/facts——规则 3 要求 draft 页不进 facts。

## 这是"rule 生效"的第三条证据

与 `cases/2026-04-20-porting-selfcheck.md` 和 `cases/2026-04-20-draft-wiki-qwen3.md` 一起，
本 case 构成 `rules/proposals/2026-04-20-seed-critical-wiki-before-first-use.md` 的
**第 3 条独立证据**。按 `.agent/evolution_policy.md` §R032（evidence ≥ 3 自动 promote），
下次跑 `python3 tools/evolve.py` 时 Step 7 应标此 proposal 为 🟢 promote_ready。

预期 promote 动作（由 `tools/promote.py` 执行）：

1. 把 proposal 正文 append 到 `rules/ACTIVE.md` 末尾
2. 把原 proposal 移到 `rules/archive/promoted-YYYY-MM-DD-<id>.md`
3. 在 `rules/ACTIVE.md` 新增条目 `promoted_from_proposal` 指回 archive
4. `docs/EVOLUTION-STATS.md` 的 `proposals_ready` 清零

## Curator Log

- **case**: 本文件（第 3 条证据）
- **memory**: 无
- **rule_proposal**: 无（此 case 的作用是**给已有 proposal 添证据**，不是新提案）
- **wiki**: 无新增
