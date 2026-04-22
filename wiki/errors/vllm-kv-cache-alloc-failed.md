---
id: vllm-kv-cache-alloc-failed
title: vLLM (Ascend) KV Cache 分配失败
kind: error
signature: "Failed to allocate KV cache"
aliases: ["INF-002", "vllm-kv-cache", "max-total-tokens", "vllm-npu-oom-start"]
tags: [inference, vllm, kv-cache, block-size, memory]
related: [vllm-ascend, 910b, mindie, cann]
stage: 推理
hardware: [910B]
framework: [vLLM, SGLang]
status: stable
last_verified: 2026-04-20
sources:
  - skill/ascend-troubleshoot/references/knowledge_base.md#INF-002
---

# vLLM / SGLang 在 NPU 上 KV Cache 分配失败

## 症状
vLLM（或 SGLang）启动时日志最后一段报 KV Cache 分配失败，服务直接退出；
或运行首轮长上下文请求时报 insufficient memory for KV cache。

## 报错示例

```
RuntimeError: Failed to allocate KV cache
# 或
RuntimeError: insufficient memory for KV cache
```

## 根因
vLLM / SGLang 在昇腾后端对内存分配较严格：
1. `max-total-tokens` 必须 > 模型 page size，否则 KV Cache 初始化失败。
2. `block-size` 与昇腾显存对齐强相关；错配会造成 20%+ 性能损失或直接分配失败。
3. 默认 `gpu-memory-utilization: 0.9` 留给动态分配的空间不足。

## 修复

### Step 1｜按模型规模设 `max-total-tokens`

| 参数量   | `--max-total-tokens` |
|----------|----------------------|
| 7B – 8B  | 1024                 |
| 13B – 14B | 2048                |
| 70B      | 4096                 |

### Step 2｜典型启动命令

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /path/to/model \
  --device npu \
  --max-model-len 4096 \
  --block-size 128 \
  --gpu-memory-utilization 0.85
```

### Step 3｜仍 OOM：降低 mem-fraction-static

```bash
--mem-fraction-static 0.8   # 默认 0.9；给动态分配更多空间
```

### Step 4｜Block size 对齐（昇腾特有）

| 场景     | 推荐 `--block-size` |
|----------|---------------------|
| 短文本   | 64                  |
| 长文本   | 128                 |
| 混合     | 128                 |

> 昇腾 NPU 对内存对齐敏感，`block-size` 选对可提升吞吐 20%+。

## 验证
```bash
# 服务正常起来；首轮请求成功
curl -s http://localhost:8000/v1/models | jq .
```

## 相关
- 显存碎片（长时间运行后 OOM）：[`wiki/errors/npu-oom-fragmentation.md`](npu-oom-fragmentation.md)
- 模型加载 OOM：`wiki/errors/oom-model-load.md` *(Wave 2 待迁 · OOM-001)*
- 上游 playbook：[`wiki/playbooks/general-debug.md`](../playbooks/general-debug.md)

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-20: 迁入 from knowledge_base.md#INF-002. source: case/2026-04-20-troubleshoot-migration-wave1
