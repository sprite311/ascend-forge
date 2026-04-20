---
name: model-adaptation
description: 把 HF/PyTorch LLM 适配到昇腾（torch_npu 或 MindSpore/MindFormers）的 SOP
trigger:
  - "适配"
  - "迁移"
  - "torch_npu"
  - "mindspore"
  - "mindformers"
  - "从 GPU 搬到"
applies_to:
  hardware: [910B, 310P]
  software: [CANN>=7.0]
version: 0.1.0
owners: [ascend-adapter]
safety: read-write
---

# 模型适配 SOP

## 何时使用

想把一个已有模型（典型是 HF 权重 + PyTorch 脚本）跑到昇腾上，且要求精度与原实现对齐。

## 前置

- 明确目标栈：
  - **路径 A**: `torch + GPU → torch_npu`（代码改动小）
  - **路径 B**: `torch → MindSpore/MindFormers`（改动大，生态深）
- 环境体检已过（见 `@ascend-env-doctor`）
- 原实现有可复现的 GPU 基线（precision/perf）

## 步骤

### 路径 A：torch_npu

1. `pip install torch_npu` 对应版本（见 `wiki/software/torch-npu.md` 版本矩阵）
2. `import torch_npu` + `device = "npu:0"`
3. 跑 forward，列出报错算子（`aten::xxx not implemented`）
4. 对每个缺失算子 → 走 [`operator-replacement`](../operator-replacement/SKILL.md)
5. 精度对齐 → 走 [`precision-alignment`](../precision-alignment/SKILL.md)

### 路径 B：MindSpore/MindFormers

1. 用 `mindformers.tools.convert` 转权重（或写自定义转换脚本）
2. 从 MindFormers 模型库找对应架构 YAML，改 config
3. 先跑 `predict` 单轮，对齐 tokenizer 输出
4. 再上 `run_predict_ms.sh` / 服务
5. 精度对齐同上

## 验证

- [ ] 固定 seed 下 logits 和 GPU 基线逐元素 cosine ≥ 0.999
- [ ] 若 generate：相同 prompt + greedy decode，输出 token 序列一致（或给出可解释偏差）
- [ ] 长序列（≥ 2048）不崩

## 失败回流

- 精度对不上 → `memory/pitfalls/precision-*.md`
- 权重转换脚本踩坑 → 固化进 `templates/`
- 如果这个模型被做过 → `wiki/models/<id>.md#adaptation-notes`

## 参考

- [MindFormers 转换文档](https://www.mindspore.cn/mindformers/docs/)
- [torch_npu 迁移指南](https://www.hiascend.com/document/)
- `wiki/models/` 下已有的模型档案
