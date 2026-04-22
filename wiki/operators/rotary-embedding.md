---
id: rotary-embedding
title: Rotary Positional Embedding (RoPE)（昇腾适配）
kind: operator
aliases: ["RoPE", "rope", "rotary"]
tags: [position, attention, ascend, torch_npu]
related: [mindie, flash-attention, torch-npu]
status: draft
last_verified: 2026-04-22
sources:
  - training-knowledge-cutoff-2025-05
  - https://arxiv.org/abs/2104.09864
  - https://www.hiascend.com/document/
---

# Rotary Positional Embedding（昇腾适配）

> ⚠️ **status: draft · source: training-knowledge-cutoff-2025-05**
> 本页内容来自模型训练截止（2025-05）前的公开资料沉淀；**未经真机复现**。
> 按 R033 回答时必须降权。升 stable 需 ≥ 2 条 case 回执。

---

## 原定义

RoPE（Su et al. 2021）把绝对位置编码为复数相位旋转，作用在 query / key 上，从而使 attention score 只依赖相对位置。
对每个 head 维度 d（偶数），把 `q[..., 2i:2i+2]` 看成复数，乘以 `e^{iθ_i * pos}`，其中 `θ_i = base^{-2i/D}`。

核心等式（HF 常见实现）：
```
q' = q * cos + rotate_half(q) * sin
k' = k * cos + rotate_half(k) * sin
```
其中 `rotate_half([a,b,c,d,...]) = [-b, a, -d, c, ...]`。

## 昇腾实现

### torch_npu 融合算子

```python
import torch_npu
# q, k: [B, N, S, D]
# cos, sin: [1, 1, S, D]  或 [B, 1, S, D]；和 HF 一样是提前算好的
q_rot, k_rot = torch_npu.npu_rotary_mul(q, cos, sin), torch_npu.npu_rotary_mul(k, cos, sin)
```

**注意**：一些老版本 torch_npu 的 API 叫 `torch_npu.npu_rotary_embedding`，参数签名可能不同；以当前 torch_npu 版本文档为准（**版本差异大**，见 `wiki/errors/torch-npu-cann-version-mismatch.md`）。

### MindSpore / MindFormers

`mindformers.modules.layers.RotaryEmbedding`（内置在 LlamaAttention / Qwen2Attention 等 cell 里）。

### ATB（底层）

ATB 提供 `Rope` 算子；torch_npu 的 `npu_rotary_mul` 本质是调 ATB。用 ATB 直接 build graph 的场景很少（MindIE 自己在做），应用层基本不直接接触。

## 两种"一半旋转"的约定（重要！）

RoPE 有**两种等价表示**，但**具体哪两维配对**的约定不同，转换不当会导致**数值错，但不报错**：

| 约定 | rotate_half 定义 | 代表实现 |
|---|---|---|
| **Neox-style（interleave 对）** | `[a,b,c,d]` → `[-c,-d,a,b]`（前一半与后一半配对） | HF LLaMA / Qwen（标准） |
| **GPT-NeoX-style（相邻对）** | `[a,b,c,d]` → `[-b,a,-d,c]`（相邻两维为一对） | GPT-J / MPT / 一些老实现 |

**昇腾踩坑**：`npu_rotary_mul` 默认用 **HF Llama 约定**（前后半对）。如果原模型用相邻对（ChatGLM、MPT 等），要**先把 q/k 重排**或换 API。
症状：模型 load 不报错，但 generate 出乱码 / 精度完全不对。

## 长上下文扩展（YaRN / NTK / Dynamic）

标准 RoPE 的 `θ_i = base^{-2i/D}`（`base` 通常 10000）只适合训练长度内。扩到 32K / 128K 需要：

- **NTK-aware**：`base *= (extended_len / trained_len)^(D/(D-2))`
- **Dynamic NTK**：运行时按 batch 实际长度调整 base
- **YaRN**（Llama 3.1 用）：分段缩放 + 注意力 temperature 调整，见 `wiki/models/llama3.md`

**昇腾端影响**：扩展逻辑在**计算 cos/sin 表**那一层，和 `npu_rotary_mul` 无关——所以这些变体都可以直接用，不需改算子。

## 精度差异（vs GPU）

- FP16：端到端 cosine ≥ 0.9999，通常无感
- BF16：同 FP16 量级
- **长序列（≥ 16K）**：三角函数查表 + 累积误差可能略放大；对齐出问题先看 `base` / `scaling` 是否算法一致

## 性能

`npu_rotary_mul` 是轻算子（相对 attention），MFU 占比很小。**不是调优重点**。

## 常见错误

| 现象 | 根因 | 修法 |
|---|---|---|
| generate 出乱码但 loss 正常 | rotate_half 约定不匹配（Neox vs NeoX） | 改 cos/sin 的 interleave 方式；或换 API |
| `size mismatch` on cos/sin | cos/sin 的 shape 是 `[S, D]` 而非 `[1, 1, S, D]` | 扩维；或传 flat 到 v1 API |
| 超长上下文精度掉 | 未加 YaRN/NTK 扩展 | 按模型对应方案调 `rope_scaling` |

## 触发本算子的典型模型

几乎所有现代 decoder-only LLM：Llama 2/3、Qwen / Qwen 2.x、DeepSeek、Mistral、Gemma、ChatGLM（Neox 变体）...

## 相关

- `wiki/operators/flash-attention.md` — RoPE 的输出是 FA 的输入
- `wiki/models/llama3.md` — YaRN 扩 128K 的参考
- `wiki/software/torch-npu.md` — npu_rotary_mul API 宿主
- `wiki/errors/torch-npu-cann-version-mismatch.md` — API 报错的常见诱因

## Backlinks
<!-- auto -->
- [flash-attention](flash-attention.md)
- [hf-to-npu-7-step](../playbooks/hf-to-npu-7-step.md)
- [mindie](../software/mindie.md)

## Changelog
- 2026-04-22: 从占位扩到完整参考页；强调两种 rotate_half 约定的踩坑点；source: training-knowledge-cutoff-2025-05；status 保持 draft 待真机复现。
- 2026-04-20: 占位创建。
