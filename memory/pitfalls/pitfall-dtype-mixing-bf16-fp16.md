---
id: pitfall-dtype-mixing-bf16-fp16
date: 2026-04-22
tags: [dtype, precision, bf16, fp16, mixed-precision, silent-bug, npu, torch]
status: active
source: training-knowledge-cutoff-2025-05
ttl_days: 365
verified_at: 2026-04-22
---

# Pitfall：BF16 / FP16 / FP32 混用导致精度漂移或显式 RuntimeError

## 现象（分两类）

### 显式错
```
RuntimeError: expected scalar type Half but found BFloat16
```
或
```
RuntimeError: "addmm_impl_cpu_" not implemented for 'BFloat16'
```
在 forward 或 optimizer step 时抛，一般是 `weight.dtype` 与 `input.dtype` 不一致。

### 静默错
- **loss 曲线看着正常**
- **eval 精度比 GPU 基线低 0.5-3%**（跑 MMLU / GSM8K 时才发现）
- **生成文本"语气对但细节偏"**（例如 number reasoning 错、代码小 bug 多）

这类比显式错更恶心，因为 CI 全过。

## 根因

HF 模型存在三个不同的 dtype 决策点，任何一个错位就会混用：

1. **`from_pretrained(torch_dtype=...)`** — 权重 load dtype
2. **`.to(dtype=...)` 或 `.half()` / `.bfloat16()`** — 手动转换
3. **AMP / autocast 配置** — 训练侧的混精包装

**昇腾特有的雷区**：
- **910B 对 BF16 原生支持好**；FP16 也支持但动态范围小
- **部分 `npu_*` 算子对 dtype 挑剔**：如 `npu_rms_norm` 的 gamma 通常要 FP32；`npu_fusion_attention` 的 q/k/v 要一致 dtype
- **RoPE 的 cos/sin 表**默认往往是 FP32，和 q/k 的 FP16/BF16 不一致会触发隐式 upcast，性能抖

## 典型错位模式

### 模式 A：load 时 FP16，但某层显式用了 BF16
```python
model = AutoModelForCausalLM.from_pretrained(
    path, torch_dtype=torch.float16,  # 全局 FP16
)
# 但 modeling_xxx.py 里 hard-code:
self.rotary_emb = RotaryEmbedding(dim=128, dtype=torch.bfloat16)  # ← 错位
```

### 模式 B：BF16 训练 + FP16 推理同一套 checkpoint
训练用 BF16 存 ckpt，推理时 `torch_dtype=torch.float16` 强转 —— 大多数权重没问题，但 **layernorm / RMSNorm 的 gamma** 在 BF16→FP16 时溢出风险大（尾数精度不同）。

### 模式 C：AMP autocast 区域不对
```python
with torch.npu.amp.autocast(dtype=torch.bfloat16):
    out = model(x)        # 里面 autocast 到 BF16
loss = F.cross_entropy(out, y)   # autocast 外，会变回 FP32 / FP16 —— 可能报 dtype mismatch
```

## 正确姿势

### 推理（绝大多数场景）

```python
# 统一 dtype，别混
model = AutoModelForCausalLM.from_pretrained(
    path,
    torch_dtype=torch.bfloat16,    # 910B/C 推荐 BF16
    attn_implementation="eager",
).npu().eval()

# 输入也显式 .to(model.dtype)
inputs = tokenizer(text, return_tensors="pt").to("npu")
for k, v in inputs.items():
    if v.is_floating_point():
        inputs[k] = v.to(model.dtype)
```

### 训练（混精）

```python
from torch_npu.npu.amp import autocast, GradScaler

scaler = GradScaler()                    # 只 FP16 需要；BF16 不需要 scaler
for batch in loader:
    optimizer.zero_grad()
    with autocast(dtype=torch.bfloat16):   # 910B 首选 BF16
        out = model(**batch)
        loss = out.loss
    loss.backward()                      # BF16 直接 backward
    optimizer.step()
```

**规则**：
- 910B / 910C 训练 **优先 BF16**（动态范围大 8bit 指数，无 loss_scale 调参）
- 老 910 / 310P 推理 **可以 FP16**
- **别混 FP16 和 BF16** —— 要么全 FP16 要么全 BF16，混用的唯一合理场景是 FP32 master weight + FP16/BF16 activation

## 诊断 snippet

```python
# 迁移后 / 新环境首次跑，加这段检查每层 dtype
for name, p in model.named_parameters():
    if p.dtype not in (torch.bfloat16, torch.float32):
        print(f"⚠️  {name}: {p.dtype}")
for name, b in model.named_buffers():
    if b.is_floating_point() and b.dtype not in (torch.bfloat16, torch.float32):
        print(f"⚠️  buffer {name}: {b.dtype}")
```

期望输出：全部 BF16 或全部 FP16，外加少量 FP32（通常 norm 的 gamma/beta）。**看到混** BF16 + FP16 就有坑。

## 何时允许 "混"

唯一合法的 "混" 是 **master weight FP32 + activation FP16/BF16**（AMP 标准做法）。
优化器的 moment 在 FP32，也合法。

## 典型触发场景

- 从 GPU 直接 load HF 权重（GPU 上默认 FP16，昇腾直接用会比 BF16 差）
- 训练用 deepspeed 的 fp16.enable=true 起，ckpt 存成 FP16，推理换成 BF16 → 精度掉
- QLoRA 的 base model FP4 + LoRA adapter FP16 + 训练 BF16 —— 三套 dtype 搅和一起

## 相关

- `memory/pitfalls/pitfall-rope-half-convention-mismatch.md`（另一个 silent bug 代表）
- `wiki/software/torch-npu.md#2026-04-22-追加npu-原生算子速查` — 算子 dtype 要求
- `wiki/playbooks/hf-to-npu-7-step.md#step-4-精度对齐必做别跳` — 首次迁移的 dtype 核对
- `skill/ascend-troubleshoot/references/knowledge_base.md`
