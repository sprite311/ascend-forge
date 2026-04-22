---
id: flash-attention
title: FlashAttention（昇腾适配）
kind: operator
aliases: ["FA", "FA2", "flash_attn", "flash-attn", "FlashAttention2"]
tags: [attention, fusion, kernel, ascend, torch_npu, atb]
related: [mindie, rotary-embedding, vllm-ascend, torch-npu]
status: draft
last_verified: 2026-04-22
sources:
  - training-knowledge-cutoff-2025-05
  - https://www.hiascend.com/document/
  - https://github.com/Ascend/ascend-transformer-boost
---

# FlashAttention（昇腾适配）

> ⚠️ **status: draft · source: training-knowledge-cutoff-2025-05**
> 本页内容来自模型训练截止（2025-05）前的公开资料沉淀；**未经真机复现**。
> 按 R033 回答时必须降权。升 stable 需 ≥ 2 条 case 回执。

---

## 原定义

FlashAttention（Tri Dao 2022）是 self-attention 的 IO-aware 融合实现：通过 tiling 和在 SRAM 上累积，把 attention 的内存访问从 O(N²) 降到 O(N)，同时避免物化完整 attention 矩阵。
- **FA1**：前向 + 反向都融合
- **FA2**：优化 warp 调度 + 减少非矩阵乘 FLOP
- **FA3**（Hopper）：不适用于昇腾

## 昇腾的定位：**不跑原始 FA CUDA kernel**

**重要**：昇腾 NPU **不运行**原始 `flash_attn` pip 包（CUDA kernel）。昇腾生态提供**功能等价的融合算子**，入口有三处：

| 场景 | torch_npu API | 底层 | 说明 |
|---|---|---|---|
| **训练 / 通用** | `torch_npu.npu_fusion_attention` | ATB | 支持 forward + backward；causal/full/varlen |
| **推理 prefill** | `torch_npu.npu_prompt_flash_attention` | ATB | 仅 forward；优化 prefill 阶段全序列计算 |
| **推理 decode** | `torch_npu.npu_incre_flash_attention` | ATB | 每步只算 1 个 new token；用于 KV cache 增量 |

**ATB**（Ascend Transformer Boost）是华为针对 Transformer 算子的加速库，位于 CANN 之上、torch_npu 之下。MindIE / vLLM-Ascend 也复用这套算子。

## `npu_fusion_attention` 调用模板（训练场景）

```python
import math, torch
import torch_npu

# query/key/value: [B, N_head, S, D_head]  或  [B, S, N_head, D_head]（看 input_layout）
out, softmax_max, softmax_sum, softmax_out = torch_npu.npu_fusion_attention(
    query, key, value,
    head_num=num_heads,
    input_layout="BNSD",         # 或 "BSND" / "SBH"
    pse=None,                    # positional shift embedding；多数场景 None
    padding_mask=None,
    atten_mask=causal_mask,      # [B, 1, S, S] bool/uint8；或 None + sparse_mode=2
    scale=1.0 / math.sqrt(D_head),
    keep_prob=1.0,               # dropout；训练时 < 1
    pre_tokens=2147483647,       # 默认全 attend 过去
    next_tokens=0,               # 严格 causal 设 0
    sparse_mode=2,               # 0:defined 1:all-mask 2:causal 3:leftUp 4:rightDown
    inner_precise=0,             # 0:high-precision 1:high-performance
)
```

**关键参数语义**：
- `sparse_mode=2` + `atten_mask=None` = full causal，**不需要**显式构造下三角 mask（最快）
- `sparse_mode=0` + 传 `atten_mask` = 任意 pattern（如 prefix-LM / doc-level mask）
- `input_layout` 决定 shape 排列；`BNSD` 最常用，`BSND` 对应 HF 默认要手 permute
- 返回四元组的后三个是 softmax 的 max/sum/out，**反向传播需要**，不能丢

## `npu_prompt_flash_attention` / `npu_incre_flash_attention`（推理）

推理分两阶段：
- **Prefill**：输入 prompt 一次性算完，用 `npu_prompt_flash_attention`
- **Decode**：每个 new token 只 attend 到历史 KV cache，用 `npu_incre_flash_attention`

```python
# decode 阶段（简化）
out = torch_npu.npu_incre_flash_attention(
    query,                       # [B, 1, N, D] — 只 1 个 new token
    key_cache, value_cache,      # [B, N_kv, S_past, D] — 历史 KV
    num_heads=num_heads,
    num_key_value_heads=num_kv_heads,  # GQA / MQA
    scale_value=1.0 / math.sqrt(D),
    input_layout="BSND",
    actual_seq_lengths=seq_lens,       # [B] 各 batch 当前实际长度
)
```

**GQA / MQA**：`num_key_value_heads` 独立于 `num_heads`。例：Qwen2-7B 是 32 query heads + 4 kv heads = GQA-8。

## 变长序列（var-len / packed）

**训练**：用 `actual_seq_qlen` / `actual_seq_kvlen`（累加前缀）而不是 padding。
**推理 prefill**：传 `actual_seq_lengths` 数组；ATB 内部走 varlen 分支。

## 精度差异（vs GPU FA2）

按公开报告经验：
- **FP16 / BF16**：端到端 cosine 相似度 ≥ 0.9999（fixed-seed greedy decode 下）
- **边缘情况可能 diff 更大**：长序列（≥ 8K）、极小头维度（D ≤ 32）、PSE 非零
- **FP32 不支持**：fused op 仅支持 FP16/BF16；想 FP32 对齐要回退 eager attention

常见 diff 来源：
1. GPU FA2 softmax 的 online/累加顺序和 ATB 略不同
2. ATB 内部 `inner_precise=1`（high-perf）走近似路径，diff 放大；对齐时设 `inner_precise=0`

## 与 `scaled_dot_product_attention` 的关系

HuggingFace Transformers 在 PyTorch 2.0+ 用 `F.scaled_dot_product_attention`（SDPA）。**昇腾 CANN 8.0 以下**SDPA 未完全 native——典型报错：
```
NotImplementedError: Could not run 'aten::_scaled_dot_product_flash_attention'
    with arguments from the 'NPU' backend.
```

**两条解法**：
1. **手工 patch**：把 `SdpaAttention` 改成调 `npu_fusion_attention`（参见 `skills/model-adaptation/`）
2. **启用 eager attention**：load 时 `attn_implementation="eager"`——慢但能跑；常用于首次对齐

## 常见错误

| 报错 | 根因 | 修法 |
|---|---|---|
| `aten::_scaled_dot_product_flash_attention not implemented` | SDPA 未 native | eager fallback 或 patch 到 `npu_fusion_attention` |
| `TypeError: npu_fusion_attention() got unexpected keyword` | torch_npu 版本差异 | 查版本矩阵；API 有过参数重命名 |
| attention 输出 `nan` | `sparse_mode=2` 但 mask 不匹配；或 scale 算错（GQA 时常漏） | 打印 mask shape；对齐先用 eager |
| 反向时 `got None, expected Tensor` | 丢了 softmax_max/sum/out 三元组 | fused 算子返回四个 tensor 都要接 |

## 性能经验（训练，910B）

粗估（**非精确数据，等真机复现**）：
- Llama-3 8B seq=4096 bs=8 训练：约 ~70% MFU（FP16），vs GPU A100 SDPA ~55%
- 随 seq_len 上升，FA 相对 eager 的加速比线性上升（8K 约 4×，16K 约 8×）

## 相关模型

触发本算子的典型模型（均在 `wiki/models/` 下）：
- `llama3` — 标准 FA2 用法
- `qwen3` — GQA + FA2
- `deepseek-v3` — MLA（multi-head latent attention）比本页更复杂，另见该页
- 任何使用 HF `transformers` 的 decoder-only LLM

## 相关

- `wiki/operators/rotary-embedding.md` — 配对使用的位置编码
- `wiki/software/torch-npu.md` — API 宿主
- `wiki/software/vllm-ascend.md` — 推理场景已内置这套调用
- `skills/model-adaptation/SKILL.md` — SDPA → npu_fusion_attention 的 patch 步骤
- `wiki/errors/torch-npu-cann-version-mismatch.md` — API 报错的常见诱因

## Backlinks
<!-- auto -->
- [hf-to-npu-7-step](../playbooks/hf-to-npu-7-step.md)
- [mindie](../software/mindie.md)
- [rotary-embedding](rotary-embedding.md)

## Changelog
- 2026-04-22: 从占位扩到完整参考页；source: training-knowledge-cutoff-2025-05；status 保持 draft 待真机复现。
- 2026-04-20: 占位创建。
