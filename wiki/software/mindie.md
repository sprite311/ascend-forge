---
id: mindie
title: MindIE (Mind Inference Engine)
kind: software
aliases: ["MindIE", "mindie", "mindieservice"]
tags: [inference, engine, huawei, ascend]
related: [cann, 910b, 310p, flash-attention, rotary-embedding]
status: stable
last_verified: 2026-04-20
sources:
  - https://www.hiascend.com/document/
---

# MindIE

## 概览
华为昇腾官方推理引擎。支持 continuous batching、PagedAttention、ATB 融合算子、OpenAI 兼容 API。
典型部署形态：`mindie-server`（HTTP 服务）或 `mindie-llm`（runtime lib）。

## 支持的模型（示意，需按版本核实）
- Qwen 系列、LLaMA 系列、InternLM、DeepSeek、ChatGLM、Baichuan、Yi…

## 关键配置
```jsonc
{
  "modelName": "qwen2-72b",
  "modelWeightPath": "/weights/qwen2-72b",
  "worldSize": 8,
  "npuDeviceIds": [[0,1,2,3,4,5,6,7]],
  "maxSeqLen": 32768,
  "maxInputTokenLen": 4096,
  "maxBatchSize": 64,
  "kvCacheType": "fp16"
}
```

## 启动
```bash
cd $MIES_INSTALL_PATH/latest
./bin/mindieservice_daemon &
tail -f logs/mindie_server_*.log
```

## 已知坑（占位）
_尚未记录。由 `ascend-deployer`/`ascend-diagnoser` 追加。_

## 相关 skill
- [`skills/mindie-deployment/SKILL.md`](../../skills/mindie-deployment/SKILL.md)

## Backlinks
<!-- auto -->

## Changelog
- 2026-04-20: 种子页创建。
