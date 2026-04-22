---
id: mindie
title: MindIE (Mind Inference Engine)
kind: software
aliases: ["MindIE", "mindie", "mindieservice", "mindie-server", "mindie-llm"]
tags: [inference, engine, huawei, ascend, openai-api, continuous-batching]
related: [cann, 910b, 910c, 310p, flash-attention, rotary-embedding, vllm-ascend]
status: stable
last_verified: 2026-04-20
sources:
  - https://www.hiascend.com/document/
---

# MindIE

## 概览
华为昇腾**官方推理引擎**，面向大模型 online serving。相对 vLLM-Ascend 的优势：官方维护 / 支持 MindSpore 系 / 多机推理成熟；相对劣势：社区小、调试工具弱。
常见形态：
- **mindie-server** — HTTP 服务进程，对外暴露 OpenAI 兼容接口
- **mindie-llm** — runtime 库，可被 Python / C++ 直接调用
- **mindie-service daemon** — 生产场景的长驻进程（`mindieservice_daemon`）

## 核心特性
- **continuous batching**（请求动态合并到同一 iteration）
- **PagedAttention**（与 vLLM 同构的显存管理）
- **ATB（Ascend Transformer Boost）融合算子**——NPU 专用的 attention / RMSNorm / rope 融合
- **OpenAI 兼容 API**（`/v1/chat/completions`, `/v1/completions`）
- **多机多卡推理**（ranktable 式 TP / PP 组合）
- **量化**：W8A8、W4A16 等（按模型支持情况）

## 支持的模型（需按安装版本核实）

> 以下为**公开资料口径**；具体以 `$MIES_INSTALL_PATH/models.yaml` 或官方 release note 为准。

常见覆盖：**Qwen / Qwen2 / Qwen3**、**LLaMA / LLaMA2 / LLaMA3**、**DeepSeek V2/V3/R1**、**InternLM 2**、**ChatGLM 2/3/4**、**Baichuan 2**、**Yi 6B/34B**。

## 版本与环境

| 组件 | 要求 |
|---|---|
| CANN | ≥ 8.0.RC1（推荐 8.3.RC1） |
| 驱动 / 固件 | 与 CANN 配套 |
| OS | 推荐 openEuler 22.03 SP3 aarch64 |
| 硬件 | 910B / 910C 生产推理；310P 有限支持 |

完整矩阵：[`cann.md`](cann.md#核心三件套pytorch--torch_npu--cann--python)。

## 关键配置（`config.json` 片段）

```jsonc
{
  "ServerConfig": {
    "ipAddress": "0.0.0.0",
    "port": 1025,
    "managementPort": 1026
  },
  "BackendConfig": {
    "modelName": "qwen2-72b-instruct",
    "modelWeightPath": "/weights/qwen2-72b",
    "worldSize": 8,
    "npuDeviceIds": [[0,1,2,3,4,5,6,7]],
    "maxSeqLen": 32768,
    "maxInputTokenLen": 4096,
    "maxPrefillBatchSize": 8,
    "maxBatchSize": 64,
    "kvCacheType": "fp16",
    "truncation": true
  }
}
```

## 启动

```bash
# 1. 加载环境
source /usr/local/Ascend/ascend-toolkit/set_env.sh
source /usr/local/Ascend/mindie/latest/mindie-service/set_env.sh

# 2. 编辑 config.json，调权重路径 / TP 规模 / maxSeqLen

# 3. 启动
cd $MIES_INSTALL_PATH/latest
./bin/mindieservice_daemon &
tail -f logs/mindie_server_*.log

# 4. 调用（OpenAI 兼容）
curl http://localhost:1025/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2-72b-instruct","messages":[{"role":"user","content":"hi"}]}'
```

## 常见坑（索引）
- [acl-507018](../errors/acl-507018.md) · 推理采样 507018（MindIE 同样适用，关 `do_sample`）
- [npu-oom-fragmentation](../errors/npu-oom-fragmentation.md) · 长跑后 OOM（建议固定 `maxSeqLen` + 定期重启）
- [docker-davinci-mount](../errors/docker-davinci-mount.md) · 容器部署必挂 davinci + 1000g shm
- [hccl-multi-node-network](../errors/hccl-multi-node-network.md) · 多机推理 ranktable

## 相关 skill
- [`skills/mindie-deployment/SKILL.md`](../../skills/mindie-deployment/SKILL.md)

## 相关模型
_由 `ascend-deployer` 按部署经历追加。_

## Backlinks
<!-- auto -->
- [310b](../hardware/310b.md)
- [310p](../hardware/310p.md)
- [910b](../hardware/910b.md)
- [910c](../hardware/910c.md)
- [acl-507018](../errors/acl-507018.md)
- [cann](cann.md)
- [deepseek-v3](../models/deepseek-v3.md)
- [flash-attention](../operators/flash-attention.md)
- [general-debug](../playbooks/general-debug.md)
- [llama3](../models/llama3.md)
- [mindformers](mindformers.md)
- [npu-oom-fragmentation](../errors/npu-oom-fragmentation.md)
- [qwen3](../models/qwen3.md)
- [rotary-embedding](../operators/rotary-embedding.md)
- [vllm-ascend](vllm-ascend.md)
- [vllm-kv-cache-alloc-failed](../errors/vllm-kv-cache-alloc-failed.md)

## Changelog
- 2026-04-20: Wave 2 填充——补 ATB / PagedAttention / continuous batching 特性、启动完整命令、常见坑索引；status 保持 stable（公开资料口径）。source: case/2026-04-20-wave2-seed-pages
- 2026-04-20: 种子页创建。
