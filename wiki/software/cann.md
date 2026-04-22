---
id: cann
title: CANN (Compute Architecture for Neural Networks)
kind: software
aliases: ["CANN", "cann-toolkit", "ascend-toolkit"]
tags: [runtime, toolkit, ascend]
related: [910b, 310p, mindie, mindspore, torch-npu, mindformers, vllm-ascend]
status: stable
last_verified: 2026-04-20
sources:
  - https://www.hiascend.com/software/cann
  - skill/ascend-troubleshoot/references/version_matrix.md
---

# CANN

## 概览
昇腾基础软件栈，包含 runtime、算子库（AICPU / AICore）、ATC 模型转换、调试工具（msprof 等）。
所有上层框架（MindSpore、torch_npu、MindIE、MindFormers、vLLM-Ascend）都依赖 CANN；
版本错配是**最常见的一类环境问题**（见 [DEP-001](../errors/torch-npu-cann-version-mismatch.md)）。

## 环境变量（高频）

```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
# 关键变量
# ASCEND_HOME_PATH      -> CANN 安装根目录
# ASCEND_OPP_PATH       -> 算子包路径
# LD_LIBRARY_PATH       -> 包含 ascend-toolkit/latest/lib64
# PYTHONPATH            -> 包含 ascend-toolkit/latest/python/site-packages
```

容器场景中建议写入 Dockerfile（见 [CTR-001](../errors/docker-davinci-mount.md)）：

```dockerfile
ENV ASCEND_HOME_PATH=/usr/local/Ascend/ascend-toolkit/latest
ENV LD_LIBRARY_PATH=/usr/local/Ascend/ascend-toolkit/latest/lib64:$LD_LIBRARY_PATH
ENV PYTHONPATH=/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:$PYTHONPATH
```

## 核心三件套：PyTorch × torch_npu × CANN × Python

> 来源：`skill/ascend-troubleshoot/references/version_matrix.md`（用户确认），`last_verified: 2026-04-20`。
> 三者必须**严格对应**；pip 单独装不对版本的组合 90% 会 segfault / HCCL undefined symbol。

| PyTorch | torch_npu | CANN         | Python    | 备注                   |
|---------|-----------|--------------|-----------|------------------------|
| 2.1.0   | 2.1.0     | 8.0.RC1+     | 3.8–3.10  | LLaMA-Factory 推荐     |
| 2.2.0   | 2.2.0     | 8.0.RC3+     | 3.8–3.10  |                        |
| 2.3.1   | 2.3.1     | 8.0.T13+     | 3.8–3.11  |                        |
| 2.4.0   | 2.4.0     | 8.3.RC1+     | 3.8–3.11  | SGLang / vLLM 推荐     |
| 2.5.0   | 2.5.0     | 8.3.RC1+     | 3.9–3.12  | 最新版，部分框架未跟进 |

## 操作系统兼容性

| 操作系统                  | 内核要求 | 架构    | 推荐程度  | 备注                      |
|---------------------------|----------|---------|-----------|---------------------------|
| openEuler 22.03 LTS SP3   | 5.10     | aarch64 | 强烈推荐  | 官方首选，问题最少        |
| openEuler 22.03 LTS SP3   | 5.10     | x86_64  | 推荐      | x86 亦支持                |
| Ubuntu 22.04 LTS          | 5.15+    | aarch64 | 推荐      | 社区资料丰富              |
| Ubuntu 20.04 LTS          | 5.4+     | aarch64 | 可用      | 多卡通信偶发问题          |
| CentOS 8                  | 4.18     | aarch64 | 勉强      | 停止维护，不推荐新项目    |
| CentOS 7                  | 3.10     | -       | 不推荐    | 内核过低，驱动安装失败    |

## 硬件型号与 CANN 版本

| 芯片型号 | 最低 CANN   | 推荐 CANN   | 显存     | 典型产品              |
|----------|-------------|-------------|----------|-----------------------|
| 910B     | 7.0         | 8.3.RC1     | 32 / 64GB | Atlas 800T A2         |
| 910C     | 8.0.RC1     | 8.3.RC1     | 64GB      | Atlas 800I A2         |
| 950PR    | CANN 2025   | 最新        | 128GB     | 2026 Q1 量产          |
| 310P     | 6.0         | 8.0.RC1     | 8 / 16GB  | Atlas 300I / 500 推理卡 |
| 310B     | 7.0         | 8.0.RC1     | 8GB       | Atlas 200I A2 边缘    |

## 推理 / 训练框架兼容性

| 框架          | 昇腾支持状态 | 最低 CANN | 推荐配合           | 备注                     |
|---------------|--------------|-----------|--------------------|--------------------------|
| vLLM          | 官方支持     | 8.0.RC3   | torch_npu 2.4.0+   | block-size 需调优        |
| SGLang        | 社区适配     | 8.3.RC1   | triton-ascend      | 需额外配置               |
| MindIE        | 华为官方     | 8.0.RC1   | 独立安装           | 多机部署推荐             |
| LLaMA-Factory | 官方支持     | 8.0.RC1   | torch_npu 2.1.0+   | NPU 训练适配最好         |
| transformers  | 间接支持     | 8.0.RC1   | torch_npu 自动迁移 | 需手动处理 cuda 硬编码   |
| ONNX Runtime  | 官方支持     | 6.0       | CANN EP            | 推理卡 (310P) 常用       |
| MindSpore     | 原生支持     | 任意      | -                  | 华为自研框架             |

## 安装要点
- 顺序：**驱动 → 固件 → CANN runtime → CANN toolkit → 上层框架**
- 不同芯片型号有独立驱动包，**不可混用**（见 [ENV-001](../errors/driver-firmware-mismatch.md)）。
- 卸载前必须 `source set_env.sh`；容器场景必须挂载 `/usr/local/Ascend`。
- 辅助依赖库缺失是隐性问题源——`pip install numpy decorator sympy cffi protobuf attrs pyyaml scipy psutil`。

## 常见坑（索引）
- [ENV-001 驱动 / 固件错配](../errors/driver-firmware-mismatch.md)
- ENV-002 set_env.sh 未生效 · `wiki/errors/set-env-not-sourced.md` *(Wave 2 待迁)*
- [DEP-001 torch / torch_npu / CANN 三件套错配](../errors/torch-npu-cann-version-mismatch.md)
- [CTR-001 容器未挂 davinci / shm-size 过小](../errors/docker-davinci-mount.md)
- 其余见 [`wiki/errors/`](../errors/)

## 相关算子 / 相关模型
_由 wiki link checker 自动维护。_

## Backlinks
<!-- auto -->
- [310b](../hardware/310b.md)
- [310p](../hardware/310p.md)
- [910b](../hardware/910b.md)
- [910c](../hardware/910c.md)
- [docker-davinci-mount](../errors/docker-davinci-mount.md)
- [driver-firmware-mismatch](../errors/driver-firmware-mismatch.md)
- [general-debug](../playbooks/general-debug.md)
- [hf-to-npu-7-step](../playbooks/hf-to-npu-7-step.md)
- [mindformers](mindformers.md)
- [mindie](mindie.md)
- [mindspore](mindspore.md)
- [npu-oom-fragmentation](../errors/npu-oom-fragmentation.md)
- [torch-npu](torch-npu.md)
- [torch-npu-cann-version-mismatch](../errors/torch-npu-cann-version-mismatch.md)
- [vllm-ascend](vllm-ascend.md)
- [vllm-kv-cache-alloc-failed](../errors/vllm-kv-cache-alloc-failed.md)

## Changelog
- 2026-04-20: 从 `skill/ascend-troubleshoot/references/version_matrix.md` 迁入版本矩阵、OS 矩阵、硬件矩阵、框架兼容性矩阵；status 升级为 stable。source: case/2026-04-20-troubleshoot-migration-wave1
- 2026-04-20: 种子页创建（值为 TBD，仅模板）。
