---
id: 2026-04-20-draft-wiki-qwen3
date: 2026-04-20
tags: [draft-wiki, qwen3, rule-evidence, seed-critical-wiki-before-first-use]
models: [qwen3]
hardware: [910b]
software: []
outcome: resolved
---

# 用户问 qwen3 上 910B 吞吐时，agent 正确降权了回答

## 用户问题

> qwen3-32b 在 910B 上 prefill / decode 大概能到多少 tokens/s？

## agent 行为

开场 SOP 命中 `wiki/models/qwen3.md`；读其 frontmatter 发现 `status: draft`。
按 `rules/proposals/seed-critical-wiki-before-first-use` 的要求，回答首行加**降权提示**：

```
⚠️ 低置信度：wiki/models/qwen3.md 当前 status=draft，以下吞吐数据基于训练记忆，
未经真机回执。请用下列命令在你的机器上核实后再引用。

（粗估，以 fp16 + batch 1 + seqlen 2048 为基线）
- prefill: ~8k~12k tokens/s/card（910B B3）
- decode: ~180~260 tokens/s/card（910B B3, kv-cache 命中）

核实命令：
  python tools/bench.py --id perf-qwen3-910b   # ⚠️ 该 bench 当前不存在，需自建
  或用 vLLM-Ascend: vllm bench throughput --model qwen3-32b ...
```

agent **拒绝**把吞吐数字写进 `memory/facts/`——按规则 3，draft 页只能写进
`rules/proposals/` 或 case 的"待验证"小节。

## 为什么这是一条"rule 生效"的证据

`rules/proposals/2026-04-20-seed-critical-wiki-before-first-use.md` 规定：
"回答任何命中 wiki 页但该页 frontmatter `status: draft` 的问题时，主 agent 必须：
(1) 首行降权提示 (2) 给验证命令 (3) 不把猜测数字写入 facts"。

本次回答**三条全部达成**。这说明：
- 用户看到的数字带了明确的"低置信度"标签，不会误当权威；
- agent 未污染 `memory/facts/`（跑 `tools/curate.py` 扫本 case，不会 hit 新 fact 候选）；
- `wiki/models/qwen3.md` 的 status 不被单次互动强行改成 "stable"——只有真机回执多次累积才升。

## 待验证

- [ ] 用户跑 `vllm bench throughput` 把真实数字回填到 `wiki/models/qwen3.md` 的
      `### 2026-0X-XX 追加：910B 回执` 小节
- [ ] 届时 curator 应把 `status: draft` 升级为 `status: stable`

## Curator Log

- **case**: 本文件（consolidation 证据，见 rule proposal）
- **memory**: 无（规则要求"draft 页不进 facts"）
- **rule_proposal**: 无
- **wiki**: 无新增（下次真机回执后才 append）
