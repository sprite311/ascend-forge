# wiki/models/

每适配一个新模型 → 新建 `<model-id>.md`。由 `ascend-adapter` 初始化，由 `ascend-tuner` / `ascend-benchmarker` 追加 tuning/perf 小节。

## 模板
```markdown
---
id: qwen2-72b
title: Qwen2-72B
kind: model
aliases: ["Qwen2 72B"]
tags: [llm, dense, chinese]
related: [qwen2-7b, mindie, flash-attention, rotary-embedding]
status: stable
last_verified: YYYY-MM-DD
sources:
  - https://hf.co/Qwen/Qwen2-72B
---

## 架构
层数 / hidden / head / KV head / rope / 激活函数 / norm / 词表

## 昇腾适配状态
- 框架：torch_npu ✅ / MindFormers ✅ / vLLM-Ascend ✅
- 引擎：MindIE ✅ / vLLM-Ascend ✅
- 替换的算子：[flash-attention](../operators/flash-attention.md), [rotary-embedding](../operators/rotary-embedding.md)

## 精度基线
## 性能基线
## 已知坑
## Tuning notes
## Changelog
```
