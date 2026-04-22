---
id: pitfall-rope-half-convention-mismatch
date: 2026-04-22
tags: [rope, rotary, attention, precision, ascend, torch_npu, silent-bug]
status: active
source: training-knowledge-cutoff-2025-05
ttl_days: 365
verified_at: 2026-04-22
---

# Pitfall：RoPE 两种 rotate_half 约定不匹配 — **loss 正常但生成乱码**

## 现象

模型从 GPU 迁移到昇腾（用 `torch_npu.npu_rotary_mul`）后：

- **loss / perplexity** 看起来正常（和 GPU 基线接近）
- **greedy decode** 出来的文本**完全乱掉** —— 不是略有偏差，是近乎随机的 token 序列
- 固定 seed 下 cosine 相似度 ~0.3（而非期望的 ≥ 0.999）

这种"loss 对但生成错"的静默 bug 特别难查，因为 training/fwd-only 指标全通过。

## 根因

RoPE 算法上有**两种等价表示**，但**具体哪两个维度配对**的约定不同：

| 约定名称 | `rotate_half([a,b,c,d])` | 代表实现 |
|---|---|---|
| **Neox-style（前后半对）** | `[-c, -d, a, b]` | **HF LLaMA / Qwen** 等绝大多数 |
| **GPT-NeoX-style（相邻对）** | `[-b, a, -d, c]` | GPT-J, MPT, 一些老 ChatGLM |

这两种表示**数学上通过重排 query/key 的维度可以互相转换**，但**同一组权重用不同约定会得到完全不同的结果**。

`torch_npu.npu_rotary_mul` 默认用**前后半对（Neox-style / HF LLaMA）**。如果原模型是相邻对（GPT-J / MPT / 某些老版本 ChatGLM 等），直接调用会算错。

## 为什么"静默"

1. **loss 正常**：在训练 step 刚开始，两种约定生成的"错误 logit"和 random init 看起来都像 noise，loss 下降曲线相似
2. **forward pass 不抛异常**：shape 对得上，数值在合理范围
3. **梯度方向并非完全随机**：只是在另一个等价空间里学，loss 能跌但学到的不是目标分布
4. **只有 generate 时出现症状**：decoder-only 的 token-by-token 采样会把细微的 rotary 错放大到语义层面

## 复现难度

**5 min vs 5 day**：如果从一开始就 fix seed + 逐层对比前 5 层输出（`allclose(gpu_out, npu_out, atol=1e-3)`），这个 bug 当天能发现。但大多数迁移的第一关只跑 loss 对齐，bug 被放行到 eval 阶段——那时模型已训上了 million-token，返工成本巨大。

## 缓解策略

### 策略 A：迁移首日做"逐层输出 diff"（强烈建议）

```python
# 在同一个输入下，让 GPU 和 NPU 都跑 forward，逐层对比
for name, (gpu_module, npu_module) in zip_modules(gpu_model, npu_model):
    gpu_out = gpu_module(x)
    npu_out = npu_module(x.npu())
    diff = (gpu_out - npu_out.cpu()).abs().max()
    print(f"{name}: max_diff={diff:.4e}")
    # 第一个 diff > 1e-2 的层就是病灶
```

**不要**跳到 eval——每次迁移都先过逐层 diff。第一个异常通常就在 RoPE 或 attention。

### 策略 B：检查模型的 RoPE 实现来源

用下面这个 grep 能定位本模型用的是哪种约定：

```bash
grep -n "rotate_half\|apply_rotary" modeling_<model>.py
```

对比 HF LLaMA 的 rotate_half（前后半对）vs GPT-J 风格（相邻对）：

```python
# HF LLaMA（前后半对，正确匹配 npu_rotary_mul）
def rotate_half(x):
    x1 = x[..., : x.shape[-1] // 2]
    x2 = x[..., x.shape[-1] // 2 :]
    return torch.cat((-x2, x1), dim=-1)

# GPT-J（相邻对，NOT matching npu_rotary_mul default）
def rotate_half(x):
    x1, x2 = x[..., ::2], x[..., 1::2]
    return torch.stack((-x2, x1), dim=-1).flatten(-2)
```

看到后者就要当心，需要**在 npu_rotary_mul 之前把 q/k 的最后一维 reshape 成前后半对**，或者**自写 rotary 的 npu kernel**。

### 策略 C：用 eager-mode 兜底对齐

首次适配时 load 模型用 `attn_implementation="eager"`，让 RoPE 跑 HF Python 实现而不走 `npu_rotary_mul`——精度对齐后再逐步换 fused 算子。

### 策略 D：社区共享的 sanity test

在 `tests/` 下加一份 `test_rope_alignment.py`（未来 skill），对任何迁入的新模型，跑：

```python
# 固定 [B, N, S, D] 的随机 q, k
# 算 GPU reference rotary
# 算 NPU npu_rotary_mul
# assert max_abs_diff < 1e-3
```

## 典型受影响模型

- **HF LLaMA 2/3 / Qwen / Mistral**：默认前后半对 ✅ 直接用
- **HF GPT-J / MPT / Falcon (老版本)**：相邻对 ⚠️ 需要 reshape / 自写
- **部分 ChatGLM-2 代码**：两种都可见 — 需要 case-by-case 验

## 相关

- `wiki/operators/rotary-embedding.md` — 算子页
- `wiki/operators/flash-attention.md` — RoPE 通常配 FA 调用
- `wiki/software/torch-npu.md`
- `memory/lessons/lesson-yaml-parser-inline-comment-and-blocklist.md` —（相似结构：静默数据错）
