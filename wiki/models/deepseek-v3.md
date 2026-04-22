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

## 2026-04-22 追加：MLA / MoE / EP 三件技术细节

> source: training-knowledge-cutoff-2025-05 · status: draft
> 本节凝练 DeepSeek-V2/V3 公开技术报告 + 昇腾侧公开案例；真机跑出请回执升 stable。

### MLA（Multi-head Latent Attention）为什么重要

V3 用 MLA 代替标准 MHA：把 K/V 先**压缩到一个 low-rank latent** `c_t` 再投影回每个 head，而不是直接存每个 head 的 K/V。

- **KV cache 大小降一个数量级**：7B 尺度上从 ~数 GB/seq 降到 ~数百 MB/seq
- **attention 计算量变**：原始 `Q·K^T` 拆成 `Q·W_q · W_k^T · c_t`，可以把 `W_q · W_k^T` 先融合
- **代价**：forward 图复杂度上升；多了 RoPE 的特殊处理（只对一部分维度施加 rope，叫 **decoupled RoPE**）

**昇腾侧实现方式**：
- MindIE ≥ 1.0.T76 左右版本通过 ATB 融合 MLA forward
- vLLM-Ascend 走 HF transformers 的 python 实现 + 融合算子 patch（性能略差 MindIE）
- 自己 patch 的话，关键是 `npu_fusion_attention` 能否吃 decoupled RoPE（部分 CANN 版本要走手写）

### MoE + Expert Parallelism（EP）拓扑

V3 有 **256 routed experts + 1 shared expert**，每 token 激活 top-8。在昇腾上部署：

| 并行维度 | 建议 | 说明 |
|---|---|---|
| TP (tensor parallel) | 4 或 8 | 单节点内，attention / MLP 分片 |
| EP (expert parallel) | 8 / 16 / 32 | 跨多节点，把 experts 分到不同卡 |
| PP (pipeline parallel) | 2-4 | 层切；只有 TP+EP 还放不下才用 |
| DP | 通常 1 | 推理很少开 |

**典型拓扑（纯推理 671B FP16）**：
- 2×8 = 16 卡 910B-64GB：TP=8, EP=16（每卡 16 experts） → 显存紧
- 4×8 = 32 卡 910B-64GB：TP=8, EP=32（每卡 8 experts） → 推荐
- 量化到 W8A8：单机 8 卡 910C-128GB 理论可以，实测需 ATB / MindIE 最新支持

### Ascend 上 MoE 的常见痛点

1. **all-to-all 通信**：EP 拆分后，每个 step 有两次跨机 all-to-all（dispatch + combine）。RoCE 200GbE 情况下，**单次 all-to-all 可能 20-50ms**——这是 V3 在 Ascend 比 GPU 慢的主因
2. **专家不均衡**：有的卡 top-8 都命中到了少数 expert，那张卡变瓶颈。V3 训练时有 aux loss 平衡，但冷启动 / 特殊 prompt 仍会偏
3. **KV cache 和专家选择的缓存不兼容**：PagedAttention 前提是 attention 对所有 token 同质处理；MoE 的 MLP 是 token-specific 的，调度复杂度 ↑↑

### 量化路线

| 方案 | 显存 | 精度损失 | 昇腾支持 |
|---|---|---|---|
| BF16 原始 | ~1340 GB（671B） | 0 | ✅（需 > 16 卡） |
| W8A8 (SmoothQuant) | ~670 GB | < 0.5% | ✅（MindIE 原生） |
| W4A16 (AWQ/GPTQ) | ~335 GB | 1-2% | ⚠️（ATB 部分 kernel） |
| FP8 | ~670 GB | 极小 | ⚠️（需 910C + CANN 最新） |

### 实战建议

- **首测跑 7B / MoE mini 版**验通路径，不要直接上 671B——**多机 all-to-all 一旦挂，整个 debug 循环 30min 起**
- 服务化**首选 MindIE**（多机推理调度成熟），vLLM-Ascend 只在单机小规模验证
- 看到 "expert 不命中" / "某卡 util < 10%"：先 profile EP 通信，再调 aux loss / router temperature

## Changelog
- 2026-04-22: 追加 MLA / MoE / EP 技术细节 + 量化路线 + 实战建议。source: training-knowledge-cutoff-2025-05. 待真机部署 ≥ 1 次回执升 stable。
- 2026-04-20: 种子页创建（Wave 2）；架构 / 适配状态 / 显存预算为公开资料口径。source: case/2026-04-20-wave2-seed-pages
