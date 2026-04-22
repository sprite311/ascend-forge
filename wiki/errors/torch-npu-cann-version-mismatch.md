---
id: torch-npu-cann-version-mismatch
title: torch / torch_npu / CANN 三件套版本不匹配
kind: error
signature: "libhccl.so: undefined symbol | HCCL error | Segmentation fault"
aliases: ["DEP-001", "three-piece-mismatch", "torch-npu-segfault", "hccl-undefined-symbol"]
tags: [environment, torch-npu, cann, version, dependency, segfault]
related: [cann, torch-npu, 910b, 910c, 310p]
stage: 环境
hardware: [全部]
status: stable
last_verified: 2026-04-20
sources:
  - skill/ascend-troubleshoot/references/knowledge_base.md#DEP-001
  - skill/ascend-troubleshoot/references/version_matrix.md
---

# torch × torch_npu × CANN 三件套版本不匹配

## 症状
- `import torch_npu` 直接报错
- 训练 / 推理偶发 Segmentation fault
- HCCL 符号缺失

## 报错示例

```
ImportError: libhccl.so: undefined symbol: xxx
RuntimeError: HCCL error
Segmentation fault (core dumped)
```

## 根因
`torch_npu` 与 `torch` 必须**主版本严格一致**；`torch_npu` 与 **CANN** 又有独立的兼容窗口。
三者错开一档 90% 报错；错开两档基本不可救。**推荐用 `wiki/software/cann.md` 的矩阵当权威表。**

## 权威版本矩阵

| PyTorch | torch_npu | CANN         | Python    | 备注                  |
|---------|-----------|--------------|-----------|-----------------------|
| 2.1.0   | 2.1.0     | 8.0.RC1+     | 3.8 – 3.10 | LLaMA-Factory 推荐    |
| 2.2.0   | 2.2.0     | 8.0.RC3+     | 3.8 – 3.10 |                       |
| 2.3.1   | 2.3.1     | 8.0.T13+     | 3.8 – 3.11 |                       |
| 2.4.0   | 2.4.0     | 8.3.RC1+     | 3.8 – 3.11 | SGLang / vLLM 推荐    |
| 2.5.0   | 2.5.0     | 8.3.RC1+     | 3.9 – 3.12 | 最新版，部分框架未跟进 |

完整见 [`wiki/software/cann.md`](../software/cann.md#核心三件套pytorch--torch_npu--cann--python)。

## 修复（推荐顺序）

### Step 1｜确诊当前版本
```bash
python -c "import torch; print('torch:', torch.__version__)"
python -c "import torch_npu; print('torch_npu:', torch_npu.__version__)"
cat /usr/local/Ascend/ascend-toolkit/latest/version.cfg | grep -i version
```

### Step 2｜按矩阵选定一组版本并重装
```bash
# 例：torch 2.1.0 + torch_npu 2.1.0 + CANN 8.0.RC1+
pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
pip install torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu
pip install torch_npu==2.1.0
```

> 务必使用 `--index-url https://download.pytorch.org/whl/cpu`——默认源会尝试装 CUDA 版 torch，拖垮 torch_npu 的依赖解析。

### Step 3｜验证
```bash
python -c "import torch, torch_npu; print('NPU available:', torch.npu.is_available())"
# 期望输出：NPU available: True
```

## 辅助依赖（DEP-002 常见连带）
```bash
pip install numpy>=1.19.2 decorator>=4.4.0 sympy>=1.5.1 cffi>=1.12.3 \
            protobuf>=3.13.0 attrs pyyaml pathlib2 scipy requests psutil absl-py
```
缺这些库会造成隐性降级（算子 fallback 到 CPU、性能异常低）。

## 相关
- 驱动 / 固件先行：[`wiki/errors/driver-firmware-mismatch.md`](driver-firmware-mismatch.md)
- CANN 页矩阵：[`wiki/software/cann.md`](../software/cann.md#核心三件套pytorch--torch_npu--cann--python)
- torch_npu 详细页：[`wiki/software/torch-npu.md`](../software/torch-npu.md)

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-20: 迁入 from knowledge_base.md#DEP-001（含 DEP-002 辅助依赖子项）. source: case/2026-04-20-troubleshoot-migration-wave1
