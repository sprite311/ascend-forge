---
name: ascend-troubleshoot
description: "昇腾 NPU 模型适配、部署、调优的结构化故障排查库。当用户提到昇腾、Ascend、NPU、CANN、torch_npu、MindSpore、Atlas、910B、910C、950、310P、MindIE、npu-smi、HCCL、AscendCL、华为 NPU 部署问题、模型迁移到昇腾、NPU 报错、ACL error、davinci 设备等关键词时触发此 skill。也适用于用户遇到 CUDA 迁移到 NPU 的问题、vLLM/SGLang/LLaMA-Factory 在昇腾上的部署、DeepSeek/Qwen/Llama 等模型在 NPU 上的适配。即使用户只是笼统地说'NPU 上跑不起来'或'昇腾报错了'，也应触发此 skill。"
---

# 昇腾 NPU 故障排查 Skill

## 概述

本 skill 提供昇腾生态（Ascend NPU）上模型适配、部署、调优的结构化故障排查能力。覆盖从环境安装到生产运行的全链路问题。

## 使用流程

### 1. 定位问题阶段

收集用户的环境信息（按优先级）：
- **硬件型号**：910B / 910C / 950 / 310P / 310B（决定驱动和 CANN 版本）
- **CANN 版本**：如 8.0.RC1 / 8.3.RC1 / CANN 2025（决定算子和框架兼容性）
- **驱动/固件版本**：`npu-smi info` 输出
- **操作系统**：openEuler / Ubuntu / CentOS + 内核版本
- **框架版本**：PyTorch + torch_npu / MindSpore / ONNX Runtime 版本
- **部署方式**：裸机 / Docker 容器 / K8s
- **模型信息**：模型名 + 参数量 + 精度（FP16/BF16/W8A8）
- **推理框架**：vLLM / SGLang / MindIE / LLaMA-Factory / 原生 transformers

### 2. 查询故障库

读取 `references/knowledge_base.md`，按以下维度匹配：
1. **错误码/报错信息**精确匹配
2. **问题阶段**匹配（安装 → 环境 → 迁移 → 训练 → 推理 → 调优）
3. **环境组合**匹配（硬件 + 软件版本组合）

### 3. 输出格式

对每个匹配的问题，输出：
```
问题：[简述]
阶段：安装/环境/迁移/训练/推理/调优
环境：硬件 + 软件版本
报错：[精确错误信息]
根因：[分析]
解决：[具体步骤]
验证：[如何确认已修复]
来源：[文档/社区/实测]
```

### 4. 未匹配时

如果故障库中没有精确匹配：
1. 根据错误码模式推断可能的原因类别
2. 提供通用排查路径（见 references/general_debug.md）
3. 建议用户提供完整的错误日志和 `npu-smi info` 输出
4. 指引用户到昇腾社区、Gitee issue 或华为云文档

## 参考文件

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| `references/knowledge_base.md` | 核心故障排查库（按阶段分类） | 每次排查时必读 |
| `references/version_matrix.md` | 软件版本兼容性矩阵 | 遇到版本兼容问题时 |
| `references/general_debug.md` | 通用排查流程和诊断命令 | 未匹配已知问题时 |
| `scripts/env_check.sh` | 环境自检脚本 | 用户不确定环境状态时 |
