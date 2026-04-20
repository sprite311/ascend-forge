# Wiki Index

> 灵感来源：Karpathy 的 "LLM Wiki" 概念——让 LLM 维护一份**自己写给自己看**的
> 交叉引用百科，知识只增不覆盖，每条都能回溯来源。
>
> 用法：主 agent 按需读取对应页；不要全量加载本目录。

---

## 分区

### Hardware (`hardware/`)
每页一个硬件型号（芯片 / 板卡 / 整机）。
- [910b](hardware/910b.md) · Atlas 910B 训推推理芯片（示例种子页）
- [310p](hardware/310p.md) · Atlas 310P 推理芯片（示例种子页）

### Software (`software/`)
每页一个软件栈组件。
- [cann](software/cann.md) · CANN（含版本矩阵模板）
- [mindie](software/mindie.md) · MindIE 推理引擎
- [mindspore](software/mindspore.md) · MindSpore 框架（占位）
- [mindformers](software/mindformers.md) · MindFormers 训推框架（占位）
- [torch-npu](software/torch-npu.md) · torch_npu 扩展（占位）
- [vllm-ascend](software/vllm-ascend.md) · vLLM-Ascend 分支（占位）

### Models (`models/`)
每页一个被适配过的模型。
_暂无条目——首次适配某模型时由 `ascend-adapter` 创建。_

### Operators (`operators/`)
每页一个算子（原定义 + 昇腾替换 + 精度/性能特征）。
_暂无条目。_

### Errors (`errors/`)
每页一个错误签名。
_暂无条目——首次诊断某错误时由 `ascend-diagnoser` 创建。_

### Playbooks (`playbooks/`)
每页一个场景化执行剧本。
_暂无条目——首次完整跑通某场景时由相应 deployer/tuner 创建。_

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
