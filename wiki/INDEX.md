# Wiki Index

> 灵感来源：Karpathy 的 "LLM Wiki" 概念——让 LLM 维护一份**自己写给自己看**的
> 交叉引用百科，知识只增不覆盖，每条都能回溯来源。
>
> 用法：主 agent 按需读取对应页；不要全量加载本目录。

---

## 分区

### Hardware (`hardware/`)
每页一个硬件型号（芯片 / 板卡 / 整机）。
- [910b](hardware/910b.md) · Atlas 910B 训推两用芯片（种子页，Wave 2 待填规格）
- [910c](hardware/910c.md) · Atlas 910C 训推两用芯片（种子页 draft）
- [310p](hardware/310p.md) · Atlas 300I / 500 推理芯片（种子页）
- [310b](hardware/310b.md) · Atlas 200I A2 边缘推理芯片（种子页 draft）

### Software (`software/`)
每页一个软件栈组件。
- [cann](software/cann.md) · CANN（含**真实版本矩阵**——PyTorch×torch_npu×CANN×Python、OS、硬件×CANN、框架兼容性）
- [mindie](software/mindie.md) · MindIE 推理引擎（占位，Wave 2 填）
- [mindspore](software/mindspore.md) · MindSpore 框架（占位）
- [mindformers](software/mindformers.md) · MindFormers 训推框架（占位）
- [torch-npu](software/torch-npu.md) · torch_npu 扩展（占位）
- [vllm-ascend](software/vllm-ascend.md) · vLLM-Ascend 分支（占位）

### Models (`models/`)
每页一个被适配过的模型。

- [qwen3](models/qwen3.md) · 通义千问 Qwen3（draft，基线待填）
- [deepseek-v3](models/deepseek-v3.md) · DeepSeek-V3 / R1（MoE，大规模推理场景）
- [llama3](models/llama3.md) · Meta Llama 3 / 3.1（长上下文）

### Operators (`operators/`)
每页一个算子（原定义 + 昇腾替换 + 精度/性能特征）。
- [flash-attention](operators/flash-attention.md) · Flash Attention（占位）
- [rotary-embedding](operators/rotary-embedding.md) · RoPE（占位）

### Errors (`errors/`)
每页一个错误签名。Wave 1 迁入 8 条高频条目（from `skill/ascend-troubleshoot/references/knowledge_base.md`）。

| 页 | 签名 / 错误码 | 类别 |
|---|---|---|
| [acl-507018](errors/acl-507018.md) | `ACL stream synchronize failed, error code:507018` | 推理 · 采样 |
| [vllm-kv-cache-alloc-failed](errors/vllm-kv-cache-alloc-failed.md) | `Failed to allocate KV cache` | 推理 · vLLM |
| [npu-oom-fragmentation](errors/npu-oom-fragmentation.md) | `NPU out of memory`（长跑后） | 推理 · 显存碎片 |
| [hccl-residual-process](errors/hccl-residual-process.md) | `EJ0001: Failed to initialize the HCCP process` | 训练 · HCCL |
| [hccl-multi-node-network](errors/hccl-multi-node-network.md) | `HCCL timeout / Network unreachable` | 训练 · 多机网络 |
| [driver-firmware-mismatch](errors/driver-firmware-mismatch.md) | `Can not find available NPU device` | 安装 · 驱动 |
| [docker-davinci-mount](errors/docker-davinci-mount.md) | `No such file: '/dev/davinci0'` | 环境 · 容器 |
| [torch-npu-cann-version-mismatch](errors/torch-npu-cann-version-mismatch.md) | `libhccl.so: undefined symbol` / Segfault | 环境 · 版本错配 |

> **Wave 2+ 迁移计划**：ENV-002/003、CTR-002、MIG-001..003、DEP-002、TRN-001/002、OOM-001、PERF-001/002、CVT-001、FW-001..003（共 15 条）。

### Playbooks (`playbooks/`)
每页一个场景化执行剧本。
- [general-debug](playbooks/general-debug.md) · 昇腾通用 6 步排查流程（`@ascend-diagnoser` 默认 SOP）

---

## 模板

### 通用 frontmatter

```yaml
---
id: <kebab-id>
title: <中文或英文>
kind: hardware|software|model|operator|error|playbook
aliases: [...]
tags: [...]
related: [<id>, <id>]
status: draft|stable|deprecated
last_verified: YYYY-MM-DD
sources:
  - <url>
---
```

### 各 kind 的推荐小节骨架

- **hardware**：概览 / 规格 / 使用注意 / 相关软件 / 相关模型 / Changelog
- **software**：概览 / 版本矩阵 / 安装 / 常见坑 / 相关算子 / 相关模型 / Changelog
- **model**：架构 / 昇腾适配状态 / 替换过的算子 / 精度基线 / 性能基线 / 已知坑 / Changelog
- **operator**：原定义 / 昇腾替换方案 / 精度差异 / 性能 / 相关模型 / Changelog
- **error**：签名 / 触发条件 / 根因 / 修复 / 引用 case / Changelog
- **playbook**：场景 / 前置 / 步骤（映射到 skills） / 验证 / 常见坑 / Changelog

### 双向链接

- 作者写 `related:`（frontmatter）
- `## Backlinks` 由 `tools/wiki_link_check.py` 自动维护
- 追加小节形如 `### YYYY-MM-DD 追加：<标题>`，在页尾 `## Changelog` 留一行

---

## 机器可读索引

`wiki/INDEX.jsonl`（每行一个 wiki 页的 frontmatter）。consolidation 时重建。
