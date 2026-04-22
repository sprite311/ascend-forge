---
id: torch-npu
title: torch_npu (Ascend PyTorch 扩展)
kind: software
aliases: ["torch_npu", "torch-npu", "ascend-pytorch", "pytorch-npu"]
tags: [pytorch, extension, ascend, runtime]
related: [cann, 910b, 910c, 310p, vllm-ascend]
status: stable
last_verified: 2026-04-20
sources:
  - https://gitee.com/ascend/pytorch
  - skill/ascend-troubleshoot/references/version_matrix.md
---

# torch_npu

## 概览
PyTorch 的**昇腾 backend 扩展**。安装后通过 `import torch_npu` 自动 monkey-patch，
让 `.cuda()` / `.to("cuda")` 等 API 在 NPU 上可用（或手动改为 `.npu()` / `.to("npu")`）。
是 vLLM-Ascend、LLaMA-Factory、SGLang 等上层库的**必需底座**。

## 核心三件套矩阵（权威）

| PyTorch | torch_npu | CANN       | Python    | 备注                  |
|---------|-----------|------------|-----------|-----------------------|
| 2.1.0   | 2.1.0     | 8.0.RC1+   | 3.8 – 3.10 | LLaMA-Factory 推荐    |
| 2.2.0   | 2.2.0     | 8.0.RC3+   | 3.8 – 3.10 |                       |
| 2.3.1   | 2.3.1     | 8.0.T13+   | 3.8 – 3.11 |                       |
| 2.4.0   | 2.4.0     | 8.3.RC1+   | 3.8 – 3.11 | SGLang / vLLM 推荐    |
| 2.5.0   | 2.5.0     | 8.3.RC1+   | 3.9 – 3.12 | 最新                  |

详：[`cann.md`](cann.md#核心三件套pytorch--torch_npu--cann--python)。
错配表现：[torch-npu-cann-version-mismatch](../errors/torch-npu-cann-version-mismatch.md)。

## 安装

```bash
# 1. 装对版本的 PyTorch（CPU 版，避免带 CUDA 依赖）
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cpu
pip install torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cpu

# 2. 装对应 torch_npu
pip install torch_npu==2.4.0

# 3. CANN set_env
source /usr/local/Ascend/ascend-toolkit/set_env.sh

# 4. 验证
python -c "import torch, torch_npu; print(torch.npu.is_available(), torch.npu.device_count())"
# 期望：True 8（以 8 卡机为例）
```

## 使用模式

### 方式 A：手动替换（推荐精细控制）
- `.cuda()` → `.npu()`
- `.to("cuda")` → `.to("npu")`
- `torch.cuda.xxx` → `torch.npu.xxx`
- `CUDA_VISIBLE_DEVICES` → `ASCEND_RT_VISIBLE_DEVICES`

### 方式 B：自动 transfer（遗留代码迁移）
```python
import torch_npu
from torch_npu.contrib import transfer_to_npu
# 自动将 .cuda() 替换为 .npu()
```

### 方式 C：仅 `import torch_npu`（最轻量）
部分 CUDA API 会被自动 monkey-patch，但复杂用法仍需手动替换。

## 常见算子限制（公开资料口径，需环境核实）
- **torch.jit.script 装饰器**在 NPU 上不完全支持（ChatGLM 等需注释，MIG-002 待迁）
- **部分 fp16/bf16 算子**精度与 CUDA 有 ε 差异——精度对齐任务走 `@ascend-tuner`
- **随机采样 kernel**在某些场景触发 [acl-507018](../errors/acl-507018.md)

## 辅助依赖（易漏）

```bash
pip install numpy>=1.19.2 decorator>=4.4.0 sympy>=1.5.1 cffi>=1.12.3 \
            protobuf>=3.13.0 attrs pyyaml pathlib2 scipy requests psutil absl-py
```

## 常见坑
- [torch-npu-cann-version-mismatch](../errors/torch-npu-cann-version-mismatch.md) · 三件套错配
- [acl-507018](../errors/acl-507018.md) · 采样 507018
- [npu-oom-fragmentation](../errors/npu-oom-fragmentation.md) · 长跑碎片 OOM
- [pitfall-sdpa-not-implemented-on-npu](../../memory/pitfalls/pitfall-sdpa-not-implemented-on-npu.md) · HF 模型默认 SDPA 落空
- [pitfall-rope-half-convention-mismatch](../../memory/pitfalls/pitfall-rope-half-convention-mismatch.md) · RoPE 约定静默错
- MIG-001 .cuda() 硬编码（待迁）
- MIG-003 DeviceType must be NPU（待迁）

## 2026-04-22 追加：NPU 原生算子速查（`torch_npu.npu_*`）

> source: training-knowledge-cutoff-2025-05 · status: draft（接口签名以本机 `help(torch_npu.xxx)` 为准）

这些是昇腾专用 fused 算子，绕过 aten 分派，直接调 ATB（Ascend Transformer Boost）。**生产推理 / 训练必须用**——不用等于把 FA / RMSNorm / RoPE 的融合红利全丢了。

### Attention 系列

| 算子 | 用途 | 典型场景 |
|---|---|---|
| `npu_fusion_attention(q, k, v, head_num, input_layout, sparse_mode, scale, ...)` | 通用 causal FA | 训练 + prefill |
| `npu_prompt_flash_attention(q, k, v, ...)` | 仅 prefill 阶段的 FA | vLLM / MindIE prefill |
| `npu_incre_flash_attention(q, k, v, ...)` | 增量 decode 阶段 FA（KV 拼接） | vLLM / MindIE decode |
| `npu_fused_infer_attention_score(...)` | 推理态统一封装（新） | MindIE 原生路径 |

**关键参数**：
- `input_layout`：`"BSND"` / `"BNSD"` / `"BSH"` / `"SBH"`，与上层模型 tensor 排布必须一致
- `sparse_mode`：`0`=无 mask（全 attention），`2`=下三角 causal，`3`=自定义 mask
- `actual_seq_lengths`：变长 batch 的真实长度列表（varlen FA）
- `scale`：`1 / sqrt(head_dim)`；别忘传，默认 1.0 会把 logit 拉爆

**最小样例（causal + BNSD）**：
```python
import torch, torch_npu, math
q = k = v = torch.randn(2, 32, 512, 128, dtype=torch.float16).npu()  # [B,N,S,D]
out, *_ = torch_npu.npu_fusion_attention(
    q, k, v,
    head_num=32,
    input_layout="BNSD",
    sparse_mode=2,                         # causal
    scale=1.0 / math.sqrt(128),
)
```

### RoPE / 位置编码

| 算子 | 用途 |
|---|---|
| `npu_rotary_mul(x, cos, sin)` | 应用 RoPE（前后半对约定） |
| `npu_apply_rotary_pos_emb(q, k, cos, sin)` | 同上封装（q/k 一次过） |

⚠️ 约定默认是 **HF LLaMA 前后半对**；GPT-J / 老 ChatGLM 是相邻对，直接调会静默错。见 [pitfall-rope-half-convention-mismatch](../../memory/pitfalls/pitfall-rope-half-convention-mismatch.md)。

### Normalization

| 算子 | 用途 |
|---|---|
| `npu_rms_norm(x, gamma, epsilon)` | RMSNorm（LLaMA / Qwen 用） |
| `npu_deep_norm(x, gx, beta, gamma, alpha, epsilon)` | DeepNorm（少见） |
| `npu_layer_norm_eval(x, normalized_shape, weight, bias, eps)` | 推理态 LayerNorm |

### 量化 / KV cache

| 算子 | 用途 |
|---|---|
| `npu_quant_matmul(x, weight, scale, ...)` | W8A8 / W4A16 量化 matmul |
| `npu_dynamic_quant(x)` | 动态 per-tensor / per-channel 量化 |
| `npu_scatter_nd_update(var, indices, updates)` | in-place KV cache 更新 |
| `npu_paged_attention(...)` | vLLM 风格 PagedAttention |

### 常用通用算子

| 算子 | 用途 |
|---|---|
| `npu_confusion_transpose(x, perm, shape, transpose_first)` | 融合 reshape+transpose |
| `npu_bmm_v2(a, b, output_sizes)` | 带 broadcast 的 batched matmul |
| `npu_masked_softmax_with_rel_pos_bias(...)` | Swin-style mask softmax |
| `npu_scaled_masked_softmax(x, mask, scale, fixed_triu_mask)` | causal softmax |

### 查 API 的四种方法

```python
# 1. dir
import torch_npu
[a for a in dir(torch_npu) if a.startswith("npu_")]

# 2. help（有 docstring 的）
help(torch_npu.npu_fusion_attention)

# 3. 看 C++ 签名
python -c "import torch_npu; print(torch_npu.npu_fusion_attention.__doc__)"

# 4. 官方 API 文档（版本对应）
# https://www.hiascend.com/document/detail/zh/canncommercial/
```

### 何时用哪个

| 场景 | 推荐 |
|---|---|
| HF 模型迁移，首次对精度 | **不用 npu_\***，用 `attn_implementation="eager"` |
| 精度 OK，上性能 | 手 patch `npu_fusion_attention`（训练+prefill） |
| 推理服务化 | `npu_prompt_flash_attention` + `npu_incre_flash_attention` 或让 vLLM-Ascend/MindIE 代劳 |
| RoPE / RMSNorm 融合 | 有空就 patch（~10-20% 额外加速） |

## 相关
- CANN：[`cann.md`](cann.md)
- vLLM-Ascend：[`vllm-ascend.md`](vllm-ascend.md)
- skill：[`skills/model-adaptation/SKILL.md`](../../skills/model-adaptation/SKILL.md)

## Backlinks
<!-- auto -->
- [910b](../hardware/910b.md)
- [910c](../hardware/910c.md)
- [acl-507018](../errors/acl-507018.md)
- [cann](cann.md)
- [flash-attention](../operators/flash-attention.md)
- [general-debug](../playbooks/general-debug.md)
- [hccl-multi-node-network](../errors/hccl-multi-node-network.md)
- [hccl-residual-process](../errors/hccl-residual-process.md)
- [hf-to-npu-7-step](../playbooks/hf-to-npu-7-step.md)
- [qwen3](../models/qwen3.md)
- [rotary-embedding](../operators/rotary-embedding.md)
- [torch-npu-cann-version-mismatch](../errors/torch-npu-cann-version-mismatch.md)
- [vllm-ascend](vllm-ascend.md)

## Changelog
- 2026-04-20: Wave 2 填充——补版本矩阵、安装命令、三种使用模式、算子限制、辅助依赖。source: case/2026-04-20-wave2-seed-pages
- 2026-04-20: 占位创建。
