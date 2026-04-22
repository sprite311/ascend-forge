---
id: mindformers
title: MindFormers
kind: software
aliases: ["MindFormers", "mindformers", "mf"]
tags: [training, llm, ascend, framework, mindspore]
related: [mindspore, cann, 910b, 910c, mindie]
status: stable
last_verified: 2026-04-20
sources:
  - https://gitee.com/mindspore/mindformers
  - https://www.mindspore.cn/mindformers
---

# MindFormers

## 概览
基于 **MindSpore** 的**大模型全流程**工具库：HuggingFace 风格的 `from_pretrained`、
预训练 / 微调 / 推理一体、覆盖主流架构（LLaMA / Qwen / DeepSeek / ChatGLM 等）。
主要面向**昇腾训练**场景；生产推理建议走 MindIE。

## 支持的模型家族
常见覆盖（按版本 release note 核实）：
- **LLaMA / LLaMA2 / LLaMA3**
- **Qwen / Qwen1.5 / Qwen2 / Qwen2.5**
- **GLM / ChatGLM3 / GLM-4**
- **DeepSeek / DeepSeek-V2 / DeepSeek-V3**
- **Baichuan / Baichuan2**
- **Yi / Yi-1.5**
- **InternLM / InternLM2**
- **Mixtral**（MoE）

## 安装

```bash
# 依赖 MindSpore + CANN
pip install mindspore==2.3.1
pip install mindformers==1.2.0    # 对齐 MindSpore 版本

# 或 git clone 开发安装
git clone https://gitee.com/mindspore/mindformers
cd mindformers
bash build.sh
```

## 典型用法

### 训练 / 微调
```bash
# 多机多卡启动（msrun）
bash scripts/msrun_launcher.sh run_llama2.yaml 8

# 或走 rank_table 方式
bash scripts/run_distribute.sh rank_table_8p.json run_llama2.yaml [0,8] 8
```

### 推理（开发期用）
```python
from mindformers import pipeline
pipe = pipeline("text_generation", model="llama2_7b")
print(pipe("你好，昇腾"))
```

> 生产推理推荐导出 `ckpt → mindie` 走 MindIE 在线服务。

## 关键配置（YAML 要点）
- `parallel_config`：`data_parallel / model_parallel / pipeline_stage` 三维并行
- `model_config.seq_length` / `batch_size` 与显存强相关
- `runner_config.epochs` / `sink_mode`（图下沉模式影响性能）

## 常见坑
- [hccl-residual-process](../errors/hccl-residual-process.md) · EJ0001 残留进程
- [hccl-multi-node-network](../errors/hccl-multi-node-network.md) · 多机 ranktable
- TRN-001 / TRN-002（待迁移）

## 相关
- 基础框架：[`mindspore.md`](mindspore.md)
- 推理部署：[`mindie.md`](mindie.md)

## Backlinks
<!-- auto -->
- [910b](../hardware/910b.md)
- [cann](cann.md)
- [deepseek-v3](../models/deepseek-v3.md)
- [hccl-multi-node-network](../errors/hccl-multi-node-network.md)
- [hccl-residual-process](../errors/hccl-residual-process.md)
- [llama3](../models/llama3.md)
- [mindspore](mindspore.md)
- [qwen3](../models/qwen3.md)

## Changelog
- 2026-04-20: Wave 2 填充——补模型家族、安装、训练/推理范例、并行配置要点。source: case/2026-04-20-wave2-seed-pages
- 2026-04-20: 占位创建。
