---
id: flash-attention
title: FlashAttention
kind: operator
aliases: ["FA", "flash_attn", "flash-attn"]
tags: [attention, fusion, kernel]
related: [mindie, rotary-embedding]
status: draft
last_verified: 2026-04-20
sources: []
---

# FlashAttention

占位页。首次在昇腾上替换/调优时，`ascend-adapter` 或 `ascend-tuner` 补以下小节：

## 原定义
Self-attention 的 IO-aware 融合实现（Tri Dao 2022）。

## 昇腾替换方案
- ATB `FlashAttention` 算子
- `torch_npu.npu_fusion_attention` / `torch_npu.npu_prompt_flash_attention`
- MindSpore 对应 cell（TBD）

## 精度差异（与 GPU）
TBD

## 性能
TBD

## 相关模型
TBD

## Backlinks
<!-- auto -->

## Changelog
- 2026-04-20: 占位创建。
