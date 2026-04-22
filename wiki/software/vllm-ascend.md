---
id: vllm-ascend
title: vLLM-Ascend
kind: software
aliases: ["vllm-ascend", "vllm_ascend", "vllm-npu", "vllm+ascend"]
tags: [inference, engine, opensource, ascend, openai-api, paged-attention]
related: [cann, torch-npu, 910b, 910c, mindie]
status: stable
last_verified: 2026-04-20
sources:
  - https://github.com/vllm-project/vllm-ascend
  - skill/ascend-troubleshoot/references/knowledge_base.md#INF-002
---

# vLLM-Ascend

## 概览
**vLLM** 的昇腾后端适配分支 / 插件。对齐 vLLM 主干的 OpenAI API、PagedAttention、continuous batching，
依赖 **torch_npu + CANN**。与 MindIE 的选择：**vLLM-Ascend** 社区活跃 / 生态对齐；**MindIE** 官方维护 / 企业支持。

## 版本与环境

| vLLM | vLLM-Ascend | torch_npu | CANN | 备注 |
|---|---|---|---|---|
| 0.6.x | 0.6.x     | 2.4.0     | 8.3.RC1+ | 推荐生产组合（公开资料口径） |
| 0.5.x | 0.5.x     | 2.4.0     | 8.0.RC3+ | 兼容维护                     |

> ⚠️ 官方矩阵请以 [vllm-ascend repo](https://github.com/vllm-project/vllm-ascend) 最新 release note 为准。

## 安装

```bash
# 1. 基础三件套
source /usr/local/Ascend/ascend-toolkit/set_env.sh
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cpu
pip install torch_npu==2.4.0

# 2. vLLM + vLLM-Ascend
pip install vllm==0.6.x                # 对齐 vllm-ascend release note
pip install vllm-ascend==0.6.x         # 或从 github 源码装

# 3. 验证
python -c "import vllm, vllm_ascend; print(vllm.__version__)"
```

## 启动（OpenAI 兼容）

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /path/to/Qwen2-72B-Instruct \
  --device npu \
  --tensor-parallel-size 8 \
  --max-model-len 4096 \
  --block-size 128 \
  --gpu-memory-utilization 0.85 \
  --port 8000
```

## 昇腾特有调参

| 参数 | 昇腾建议 | 说明 |
|---|---|---|
| `--block-size`        | **64 / 128**（不要默认 16） | 与 page size 对齐；短文 64，长文/混合 128 |
| `--max-total-tokens`  | 7B: 1024 / 13B: 2048 / 70B: 4096 | 必须 > 模型 page size |
| `--gpu-memory-utilization` | 0.85 | 避免长跑后 OOM |
| `--mem-fraction-static` | 0.8 | 给动态分配留空间 |
| `--tensor-parallel-size` | 等于 NPU 数 / 模型 TP 分片数 | 结合显存预算 |

详见 [vllm-kv-cache-alloc-failed](../errors/vllm-kv-cache-alloc-failed.md) 与
[pitfall-block-size-alignment](../../memory/pitfalls/pitfall-block-size-alignment.md)。

## 已知差异（vs CUDA vLLM）
- **block-size 默认值**不同（参见上表）
- **采样算子**在某些组合下触发 [acl-507018](../errors/acl-507018.md)；关 `do_sample` 或降 temperature 规避
- **显存碎片**更敏感：长跑后 OOM 见 [npu-oom-fragmentation](../errors/npu-oom-fragmentation.md)
- 部分 attention 优化（FlashAttention 变体）昇腾侧走 **ATB** 融合算子，行为与 CUDA 不完全等价

## 常见坑（索引）
- [vllm-kv-cache-alloc-failed](../errors/vllm-kv-cache-alloc-failed.md) · KV Cache 分配失败
- [npu-oom-fragmentation](../errors/npu-oom-fragmentation.md) · 长跑 OOM
- [acl-507018](../errors/acl-507018.md) · 采样 507018
- [torch-npu-cann-version-mismatch](../errors/torch-npu-cann-version-mismatch.md) · 三件套错配

## 相关
- torch_npu：[`torch-npu.md`](torch-npu.md)
- 官方对手：[`mindie.md`](mindie.md)
- skill：[`skills/vllm-ascend-serving/SKILL.md`](../../skills/vllm-ascend-serving/SKILL.md)

## Backlinks
<!-- auto -->
- [acl-507018](../errors/acl-507018.md)
- [cann](cann.md)
- [deepseek-v3](../models/deepseek-v3.md)
- [flash-attention](../operators/flash-attention.md)
- [hf-to-npu-7-step](../playbooks/hf-to-npu-7-step.md)
- [llama3](../models/llama3.md)
- [mindie](mindie.md)
- [npu-oom-fragmentation](../errors/npu-oom-fragmentation.md)
- [qwen3](../models/qwen3.md)
- [torch-npu](torch-npu.md)
- [vllm-kv-cache-alloc-failed](../errors/vllm-kv-cache-alloc-failed.md)

## Changelog
- 2026-04-20: Wave 2 填充——补版本矩阵、安装 / 启动命令、昇腾特有调参表、与 CUDA 差异、错误索引。source: case/2026-04-20-wave2-seed-pages
- 2026-04-20: 占位创建。
