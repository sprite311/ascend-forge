---
id: qwen3
title: Qwen3 系列
kind: model
aliases: ["Qwen3", "qwen3", "Tongyi Qianwen 3"]
tags: [llm, qwen, alibaba, decoder-only, chat]
related: [910b, 910c, mindie, vllm-ascend, mindformers, torch-npu]
status: draft
last_verified: 2026-04-20
sources:
  - https://github.com/QwenLM/Qwen3
  - https://huggingface.co/Qwen
  - skill/ascend-troubleshoot/references/knowledge_base.md
---

# Qwen3

> ⚠️ **种子页（status: draft）**——Qwen3 系列由阿里通义实验室发布，版本 / 具体 SKU 在迭代中；
> 具体精度 / 性能数据以用户实际跑出为准。

## 概览
阿里 **通义千问 Qwen3** 系列，decoder-only 架构，Qwen2 → Qwen2.5 → Qwen3 的迭代延续。
**昇腾适配度**：高（Qwen 家族是昇腾社区最"顺"的模型家族，见
[skill/ascend-troubleshoot/references/version_matrix.md#模型适配状态]）。

## 架构要点
- Decoder-only, GQA（grouped query attention）
- RoPE（[`wiki/operators/rotary-embedding.md`](../operators/rotary-embedding.md)）
- RMSNorm
- SwiGLU FFN
- 部分 SKU 为 MoE（`Qwen3-MoE-*`）

## 昇腾适配状态（公开资料口径）

| 场景   | 状态 | 推荐组合                              |
|--------|------|---------------------------------------|
| 训练   | ✅   | MindFormers / LLaMA-Factory + 910B/C  |
| 微调   | ✅   | LLaMA-Factory（NPU 训练适配最好）     |
| 推理   | ✅   | MindIE / vLLM-Ascend                  |
| 量化   | ✅   | W8A8（主流）、W4A16（显存紧张时）     |

## 常用部署

### vLLM-Ascend
```bash
python -m vllm.entrypoints.openai.api_server \
  --model /weights/Qwen3-72B-Instruct \
  --device npu \
  --tensor-parallel-size 8 \
  --max-model-len 32768 \
  --block-size 128 \
  --gpu-memory-utilization 0.85
```

### MindIE
见 [`mindie.md#关键配置`](../software/mindie.md#关键配置configjson-片段)；把 `modelName` 改为具体 Qwen3 SKU。

## 替换过的算子
_由 `ascend-adapter` 按适配经历追加。_

## 精度基线
_由 `ascend-tuner` 按对齐任务追加（基线 vs CUDA 的 max abs diff / KL divergence）。_

## 性能基线
_由 `ascend-benchmarker` 按基准任务追加（TPS、首 token 时延、长文延迟）。_

## 已知坑
- [acl-507018](../errors/acl-507018.md) · 采样相关：必要时关 `do_sample`
- [vllm-kv-cache-alloc-failed](../errors/vllm-kv-cache-alloc-failed.md) · 长上下文必须调 `--max-model-len` + `--block-size=128`

## 相关
- 硬件：[`910b`](../hardware/910b.md) / [`910c`](../hardware/910c.md)
- 推理引擎：[`mindie`](../software/mindie.md) / [`vllm-ascend`](../software/vllm-ascend.md)

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-22: 追加 Qwen2/2.5 实战细节（source: training-knowledge-cutoff-2025-05）；**标注 Qwen3 截止期内信息不全**，需真机回执修正。
- 2026-04-20: 种子页创建（Wave 2）；架构 / 适配状态 / 部署命令为公开资料 + 昇腾社区口径；基线字段空待填。source: case/2026-04-20-wave2-seed-pages
