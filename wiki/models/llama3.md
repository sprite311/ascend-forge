---
id: llama3
title: Llama 3 / 3.1 系列
kind: model
aliases: ["Llama3", "llama3", "LLaMA 3", "Llama-3", "Llama 3.1"]
tags: [llm, llama, meta, decoder-only, chat]
related: [910b, 910c, mindie, vllm-ascend, mindformers]
status: draft
last_verified: 2026-04-20
sources:
  - https://github.com/meta-llama/llama3
  - https://huggingface.co/meta-llama
  - skill/ascend-troubleshoot/references/knowledge_base.md
---

# Llama 3 / 3.1

> ⚠️ **种子页（status: draft）**——实际适配 / 性能以用户环境跑出为准。

## 概览
Meta 开源的 **Llama 3** 系列（8B / 70B / 405B）及 **3.1**（增强 128K 上下文、tool use）。
**昇腾适配度**：高（无重大硬编码问题，见昇腾社区记录）。

## 架构要点
- Decoder-only, GQA
- RoPE（YaRN / NTK 变体，长上下文）
- RMSNorm
- SwiGLU FFN
- Llama 3.1 起支持 **128K context**

## 昇腾适配状态

| 场景   | 状态 | 推荐组合                               |
|--------|------|----------------------------------------|
| 训练   | ✅   | LLaMA-Factory + 910B/C                 |
| 微调   | ✅   | LoRA / QLoRA / Full；LLaMA-Factory     |
| 推理   | ✅   | MindIE / vLLM-Ascend                   |
| 量化   | ✅   | W8A8 / W4A16                           |

## 硬件预算（FP16）

| SKU   | FP16 显存 | W8A8 显存 | 推荐卡                  |
|-------|-----------|-----------|-------------------------|
| 8B    | ~16 GB    | ~8 GB     | 910B-32GB × 1           |
| 70B   | ~140 GB   | ~70 GB    | 910B-64GB × 4（推理）   |
| 405B  | ~810 GB   | ~405 GB   | 910B/C 多机             |

## 常用部署（vLLM-Ascend）

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /weights/Llama-3.1-70B-Instruct \
  --device npu \
  --tensor-parallel-size 8 \
  --max-model-len 131072 \
  --block-size 128 \
  --gpu-memory-utilization 0.85
```

## 已知坑
- **128K 上下文**：`--max-model-len` 开到 128K 会吃满显存，建议按实际 workload 缩到 32K / 64K
- [npu-oom-fragmentation](../errors/npu-oom-fragmentation.md) · 长跑碎片
- [acl-507018](../errors/acl-507018.md) · 采样 507018（推理框架通用）

## 替换过的算子
_由 `ascend-adapter` 追加。_

## 精度 / 性能基线
_由 `ascend-tuner` / `ascend-benchmarker` 追加。_

## 相关
- 硬件：[`910b`](../hardware/910b.md) / [`910c`](../hardware/910c.md)
- 推理：[`mindie`](../software/mindie.md) / [`vllm-ascend`](../software/vllm-ascend.md)
- 训练：[`mindformers`](../software/mindformers.md)

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-22: 追加迁移配方 + 踩坑清单（source: training-knowledge-cutoff-2025-05）；仍 draft 待真机。
- 2026-04-20: 种子页创建（Wave 2）；架构 / 适配 / 显存预算为公开资料口径。source: case/2026-04-20-wave2-seed-pages
