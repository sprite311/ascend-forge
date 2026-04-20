---
name: memory-optimization
description: 显存不够 / OOM / KV Cache 爆 → 显存优化手段
trigger: ["oom", "显存", "kv cache", "acl_error_500002", "memory"]
applies_to:
  hardware: [910B, 310P]
  software: [CANN>=7.0]
version: 0.1.0
owners: [ascend-tuner]
safety: read-write
---

# 显存优化 SOP

## 先诊断

```bash
npu-smi info                    # 总览
npu-smi info -t memory -i 0     # 逐卡显存
```

关键估算（推理）：
```
权重显存 ≈ n_params × dtype_bytes / TP
KV 缓存 ≈ max_num_seqs × max_model_len × 2 × n_layer × n_kv_head × head_dim × dtype_bytes
激活显存 ≈ ~batch × seq × hidden × 若干倍
```

## 手段（按"副作用"从小到大）

1. **调 KV 预算**：降 `max_num_seqs`、`max_model_len`、开 `chunked prefill`
2. **量化**：
   - **W8A8**（推荐起步，精度损失小）
   - **W4A16**（激进，需验精度）
   - **AWQ / SmoothQuant**（激活敏感时）
3. **Tensor Parallel**：增大 TP，权重摊到更多卡（带宽代价）
4. **Pipeline Parallel**：长 pipeline，bubble 代价
5. **offload**：把不常用的 KV / 权重 offload 到 host（时延代价）
6. **激活重计算**：训练场景下换算力省显存

## 推理场景常用组合

| 场景 | 推荐 |
|---|---|
| 单机 8×910B，72B 模型 | TP=8 + W8A8，max_num_seqs=32~64 |
| 单机 8×910B，14B 模型 | TP=2~4 + FP16，max_num_seqs=128+ |
| 310P 边缘 | W4A16 必选 |

## 失败回流
- 新的 OOM 报错 → `wiki/errors/acl-500002-*.md`
- 量化导致精度掉 → 回到 `precision-alignment`

## 参考
- `wiki/operators/flash-attention.md`（KV Cache 实现相关）
- 量化工具：`msmodelslim`、`atc` 量化流程
