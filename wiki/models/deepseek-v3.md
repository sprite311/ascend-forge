---
id: deepseek-v3
title: DeepSeek-V3 系列
kind: model
aliases: ["DeepSeek-V3", "deepseek-v3", "DeepSeek V3", "DeepSeek-R1"]
tags: [llm, deepseek, moe, decoder-only, chat, large]
related: [910b, 910c, mindie, vllm-ascend, mindformers]
status: draft
last_verified: 2026-04-20
sources:
  - https://github.com/deepseek-ai/DeepSeek-V3
  - https://huggingface.co/deepseek-ai
  - skill/ascend-troubleshoot/references/knowledge_base.md
---

# DeepSeek-V3

> ⚠️ **种子页（status: draft）**——规格 / 适配状态以用户实际跑出为准。

## 概览
DeepSeek 开源的**大规模 MoE 模型**（活跃参数 ~37B，总参 671B）。
包括 base、chat、R1（推理增强）等 SKU。对昇腾的要求极高——**显存大 + MoE 专家路由 + 长上下文**。

## 架构要点
- **MoE** — 稀疏专家，每 token 激活少数专家
- **MLA**（Multi-head Latent Attention）— DeepSeek 原创的 KV 压缩机制
- **长上下文**（128K+）
- **FP8 / BF16 混精**（V3 原生支持）

## 昇腾适配状态（公开资料口径）

| 场景   | 状态 | 推荐组合                                         |
|--------|------|--------------------------------------------------|
| 训练   | ⚠️   | MindFormers（支持但需多机 PP + TP + EP 并行）   |
| 推理   | ✅   | **MindIE**（多机首选）/ vLLM-Ascend（单机 TP）  |
| 量化   | ✅   | W8A8 常用；FP8 需硬件 + runtime 支持             |

## 硬件预算（FP16 / BF16）

| 模式       | 显存估算     | 推荐拓扑              |
|------------|--------------|-----------------------|
| 激活 (MoE) | ~74 GB       | 910B-64GB × 8 起      |
| W8A8       | ~37 GB       | 910B-64GB × 4–8       |
| 训练       | TB 级        | 910B/C 集群多机多卡   |

详：[`skill/ascend-troubleshoot/references/knowledge_base.md#OOM-001`](../../skills/ascend-troubleshoot/references/knowledge_base.md)

## 常用部署

### MindIE（多机 TP / PP）
涉及 ranktable + 多机启动脚本，见 [`mindie.md`](../software/mindie.md) + [hccl-multi-node-network](../errors/hccl-multi-node-network.md)。

### vLLM-Ascend（单机大显存场景）
```bash
python -m vllm.entrypoints.openai.api_server \
  --model /weights/DeepSeek-V3 \
  --device npu \
  --tensor-parallel-size 8 \
  --max-model-len 16384 \
  --block-size 128 \
  --gpu-memory-utilization 0.90
```

## 替换过的算子
_由 `ascend-adapter` 追加。MLA / MoE 路由算子是 CUDA→NPU 对齐的重点。_

## 精度 / 性能基线
_由 `ascend-tuner` / `ascend-benchmarker` 追加。_

## 已知坑
- [hccl-multi-node-network](../errors/hccl-multi-node-network.md) · 多机必调 ranktable
- [npu-oom-fragmentation](../errors/npu-oom-fragmentation.md) · 长上下文长跑后 OOM
- MoE 专家不均衡导致某些卡打爆（性能基线阶段观察）

## 相关
- 硬件：[`910b`](../hardware/910b.md) / [`910c`](../hardware/910c.md)
- 推理：[`mindie`](../software/mindie.md) / [`vllm-ascend`](../software/vllm-ascend.md)

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-20: 种子页创建（Wave 2）；架构 / 适配状态 / 显存预算为公开资料口径。source: case/2026-04-20-wave2-seed-pages
