---
id: pitfall-block-size-alignment
kind: pitfall
tags: [inference, vllm, block-size, memory, alignment, perf]
source: skill/ascend-troubleshoot/references/knowledge_base.md#INF-002
created_at: 2026-04-20
verified_at: 2026-04-20
confidence: high
ttl_days: 180
related_wiki: [vllm-ascend, 910b, cann]
---

## 坑
vLLM / SGLang 在昇腾后端的 `--block-size` 参数**不可用默认值**（CUDA 默认 16）。
昇腾 NPU 对内存对齐敏感：block-size 与 page size 不对齐时，
- **轻则**性能下降 20%+
- **重则**直接 KV Cache 分配失败（见 [`wiki/errors/vllm-kv-cache-alloc-failed.md`](../../wiki/errors/vllm-kv-cache-alloc-failed.md)）

## 规避
| 场景     | `--block-size` |
|----------|----------------|
| 短文本   | 64             |
| 长文本   | 128            |
| 混合     | 128（推荐默认） |

同时确保 `--max-total-tokens` > 模型 page size：
- 7B–8B：1024
- 13B–14B：2048
- 70B：4096

## 检测
vLLM 启动日志中 `block_size=` 若为 16 → 立即改为 128 重试。

## 参考
- 错误页：[`wiki/errors/vllm-kv-cache-alloc-failed.md`](../../wiki/errors/vllm-kv-cache-alloc-failed.md)
- case：[`cases/2026-04-20-troubleshoot-migration-wave1.md`](../../cases/2026-04-20-troubleshoot-migration-wave1.md)
