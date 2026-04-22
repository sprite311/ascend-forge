---
id: npu-oom-fragmentation
title: NPU 显存碎片导致长时间运行后 OOM
kind: error
signature: "NPU out of memory (after long running)"
aliases: ["INF-003", "fragmentation-oom", "long-running-oom"]
tags: [inference, memory, fragmentation, long-running, production]
related: [910b, 910c, cann, mindie, vllm-ascend]
stage: 推理
hardware: [910B, 910C]
status: stable
last_verified: 2026-04-20
sources:
  - skill/ascend-troubleshoot/references/knowledge_base.md#INF-003
---

# NPU 显存碎片 · 长时间运行后 OOM

## 症状
服务刚启动时一切正常，连续运行几小时后开始 OOM；`torch.npu.memory_stats()` 显示高碎片率。

## 报错示例

```
RuntimeError: NPU out of memory. Tried to allocate X GiB
```

## 根因
昇腾 NPU 对显存碎片比 CUDA 更敏感：
1. Python GC 在 NPU 上释放不及时。
2. **动态 shape** 的推理请求（长短不一、padding 不对齐）加剧碎片化。
3. 无 compaction 机制，碎片只能靠 `empty_cache` 或重启回收。

## 修复（按长期稳定性排序）

### 方案 1｜主动释放（进程内）
```python
import torch, torch_npu, gc

# 每轮 generate 后
torch.npu.empty_cache()
gc.collect()
```

### 方案 2｜固定 Input Shape（最有效）
- 对输入 padding 到固定长度（如 2048 / 4096）
- 缩小动态 shape 的变化范围；必要时分桶（bucketing）。

### 方案 3｜碎片监测

```python
stats = torch.npu.memory_stats()
print(f"碎片率: {stats.get('fragmentation', 'N/A')}")
print(f"活跃: {stats.get('active.all.current', 'N/A')}")
print(f"保留: {stats.get('reserved_bytes.all.current', 'N/A')}")
```

### 方案 4｜定期滚动重启（生产务实方案）
```yaml
# 例：K8s liveness / cron 低峰期滚动重启
# 每 6–12 小时触发一次 graceful restart
livenessProbe:
  exec:
    command: ["/bin/sh","-c","test $(date +%H) -ne 3 -a $(uptime -s_to_seconds) -lt 21600"]
  periodSeconds: 60
```

## 优化原则
> **环境要对齐 · Shape 要固定 · 线程要限制**

## 验证
```bash
# 连续 24h+ 无 OOM 视为通过
# 记录：
#   torch.npu.max_memory_allocated()
#   fragmentation ratio 随时间曲线
```

## 相关
- 启动时 OOM（非碎片）：`wiki/errors/oom-model-load.md` *(Wave 2 待迁 · OOM-001)*
- KV Cache 分配失败：[`wiki/errors/vllm-kv-cache-alloc-failed.md`](vllm-kv-cache-alloc-failed.md)
- 上游 playbook：[`wiki/playbooks/general-debug.md`](../playbooks/general-debug.md)

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-20: 迁入 from knowledge_base.md#INF-003. source: case/2026-04-20-troubleshoot-migration-wave1
