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
- MIG-001 .cuda() 硬编码（待迁）
- MIG-003 DeviceType must be NPU（待迁）

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
- [general-debug](../playbooks/general-debug.md)
- [hccl-multi-node-network](../errors/hccl-multi-node-network.md)
- [hccl-residual-process](../errors/hccl-residual-process.md)
- [qwen3](../models/qwen3.md)
- [torch-npu-cann-version-mismatch](../errors/torch-npu-cann-version-mismatch.md)
- [vllm-ascend](vllm-ascend.md)

## Changelog
- 2026-04-20: Wave 2 填充——补版本矩阵、安装命令、三种使用模式、算子限制、辅助依赖。source: case/2026-04-20-wave2-seed-pages
- 2026-04-20: 占位创建。
