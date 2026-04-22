---
id: hf-to-npu-7-step
title: HuggingFace LLM → 昇腾 910B 迁移 7 步 Playbook
kind: playbook
aliases: ["hf-to-npu", "hf-migration", "迁移 playbook"]
tags: [migration, adaptation, 910b, torch-npu, hf, decoder-only]
related: [torch-npu, cann, vllm-ascend, mindie, flash-attention, rotary-embedding]
status: draft
last_verified: 2026-04-22
sources:
  - training-knowledge-cutoff-2025-05
  - skills/model-adaptation/SKILL.md
---

# HF LLM → 昇腾 910B 迁移 7 步 Playbook

> ⚠️ **status: draft · source: training-knowledge-cutoff-2025-05**
> 这是把公开报告的迁移经验浓缩的**默认路径**；在你的具体模型 + 客户环境下**可能有偏差**。
> 按 R033 回答时降权；升 stable 需 ≥ 2 条真机 case 回执。

---

## 适用范围

- 模型：HuggingFace 上发布的**decoder-only LLM**（Llama 2/3、Qwen 2/2.5、Mistral、DeepSeek V2/V3、Yi、ChatGLM-3/4 等）
- 目标：在 Atlas 800T A2（8×910B）上**精度对齐 + 跑起来**
- **不适用**：多模态（VL / Audio）、Encoder-Decoder（T5 等）、MoE 专家路由（需要额外 patch）

## Step 1 · 环境三件套 self-check（30 min）

```bash
# driver + firmware
npu-smi info

# CANN
cat /usr/local/Ascend/ascend-toolkit/latest/aarch64-linux/ascend_toolkit_install.info

# torch_npu
python -c "import torch, torch_npu; print(torch.__version__, torch_npu.__version__)"
```

对照 `memory/facts/fact-torch-npu-version-matrix-25q1.md` 查组合是否合法。**如果不在表里**，先调环境，不要动模型——环境不对后面全是玄学。

详见 `wiki/errors/torch-npu-cann-version-mismatch.md`、`wiki/errors/driver-firmware-mismatch.md`。

## Step 2 · 权重 + tokenizer 本地化（10-60 min）

```bash
# 推荐用 modelscope（国内速度远好于 HF）
pip install modelscope
python -c "from modelscope import snapshot_download; \
  snapshot_download('qwen/Qwen2-7B-Instruct', cache_dir='/weights')"
```

权重格式：**safetensors 直接用**，不需要转 MindSpore checkpoint（除非走 MindFormers 路线）。

## Step 3 · 首次 load（eager 模式对精度）

```python
import torch, torch_npu
from transformers import AutoModelForCausalLM, AutoTokenizer

model_path = "/weights/Qwen2-7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16,
    attn_implementation="eager",     # ← 首次必用 eager，避开 SDPA 坑
    trust_remote_code=True,
).npu().eval()
```

**90% 迁移第一个坑**：不加 `attn_implementation="eager"` 会报 SDPA not implemented。
见 `memory/pitfalls/pitfall-sdpa-not-implemented-on-npu.md`。

## Step 4 · 精度对齐（必做，别跳）

```python
# 固定 seed，greedy decode，打印前 20 token
torch.manual_seed(42)
prompt = "The capital of France is"
inputs = tokenizer(prompt, return_tensors="pt").to("npu")
outputs = model.generate(**inputs, max_new_tokens=20, do_sample=False)
print(tokenizer.decode(outputs[0]))
```

和 GPU 基线对比**首 20 token 必须完全一致**。如果不一致：
- **logit 对不上**：先查 RoPE 约定（见 `pitfall-rope-half-convention-mismatch`）、再查 dtype（FP16 vs BF16 混用）
- **token 对不上但 logit 近似**：采样配置问题（`do_sample`, `temperature`）

**别跳过这一步直接上服务化**——一旦上了服务化，debug 成本翻 10 倍。

## Step 5 · 算子 fusion（性能起飞）

精度 OK 后，把 `attn_implementation="eager"` 换成 `"sdpa"`（CANN 8.0+）或手 patch `npu_fusion_attention`：

```python
# 方式 1：如果 CANN 够新
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16,
    attn_implementation="sdpa",
    trust_remote_code=True,
).npu()

# 方式 2：手 patch（生产推理用法；见 wiki/operators/flash-attention.md）
```

重跑 Step 4 的 smoke test——**换 FA 后必须再对一次精度**（容易 0.1% 偏差）。

## Step 6 · 长序列压力（选做）

```python
# 压到目标 max_model_len
inputs = tokenizer("a"*30000, return_tensors="pt", truncation=False).to("npu")
out = model.generate(**inputs, max_new_tokens=100)
```

**常见问题**：
- OOM 碎片化 → 见 `wiki/errors/npu-oom-fragmentation.md`
- RoPE 超出训练长度 → 配 `rope_scaling`（YaRN for Llama 3.1，见 `wiki/models/llama3.md`）

## Step 7 · 服务化（vLLM-Ascend 或 MindIE）

**vLLM-Ascend**（生态近 HF）：
```bash
python -m vllm.entrypoints.openai.api_server \
  --model /weights/Qwen2-7B-Instruct \
  --device npu \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --block-size 128 \           # 必须 64/128，见 pitfall-block-size-alignment
  --gpu-memory-utilization 0.85
```

**MindIE**（原生深度优化）：见 `wiki/software/mindie.md`。

## 把所有时间加起来

| 阶段 | 首次 | 熟练后 |
|---|---|---|
| Step 1 环境自检 | 30 min - 2 h（新机器） | 5 min |
| Step 2 权重本地化 | 30-60 min | 10 min |
| Step 3 + 4 精度对齐 | **1-2 天**（踩坑） | 2 h |
| Step 5 FA fusion | 1 h - 0.5 天 | 20 min |
| Step 6 长序列 | 2-4 h（按需） | 1 h |
| Step 7 服务化 | 2-4 h | 30 min |
| **合计** | **3-5 天**（首次） | **4-6 h**（熟练） |

这就是小组"5 天 → 0-1 天"目标的理论基础：**熟练 + playbook + 踩过的坑都沉淀** → 从 3-5 天压缩到半天到 1 天。

## 何时这条 playbook 不够用

- **MoE 模型**：专家路由 / all-to-all 在昇腾上需要额外 patch
- **超长上下文 > 128K**：attention 算法变（Ring Attention / Blockwise），当前 playbook 不覆盖
- **多模态**：需要 vision encoder 适配，走单独 skill
- **训练（非推理）**：需要额外考虑 HCCL 通信、gradient checkpointing、ZeRO/FSDP 在 NPU 的对应

## 相关

- `skills/model-adaptation/SKILL.md` — 更细的 SOP
- `memory/pitfalls/pitfall-sdpa-not-implemented-on-npu.md`
- `memory/pitfalls/pitfall-rope-half-convention-mismatch.md`
- `memory/pitfalls/pitfall-block-size-alignment.md`
- `memory/facts/fact-torch-npu-version-matrix-25q1.md`
- `wiki/operators/flash-attention.md`
- `wiki/operators/rotary-embedding.md`

## Changelog

- 2026-04-22: 初版。浓缩自训练数据中多份公开迁移报告。待真机 ≥ 2 次成功回执升 stable。
