---
id: fact-ascend-hardware-specs
date: 2026-04-22
tags: [hardware, 910b, 910c, 310p, 310b, atlas, specs]
status: active
source: training-knowledge-cutoff-2025-05
ttl_days: 365
verified_at: 2026-04-22
---

# 事实：昇腾主流 SKU 规格速查（公开资料口径）

> **source**: training-knowledge-cutoff-2025-05
> **注意**：显存、算力、功耗为**公开资料口径**（华为 datasheet / 白皮书），
> 真机实际值可能因 SKU 细分 / 批次 / 固件略有差异。

## 训练 / 推理卡

| SKU | 定位 | HBM 显存 | FP16/BF16 算力 | TDP | 典型服务器 |
|---|---|---|---|---|---|
| **910B** | 训练 + 推理 | 32GB / 64GB | ~280-320 TFLOPS | ~392W | Atlas 800T A2（8 卡） |
| **910B2** | 训练 | 64GB | ~280 TFLOPS | ~400W | Atlas 800T A2 新批次 |
| **910B3** | 训练 | 64GB | ~300+ TFLOPS | ~400W | Atlas 800T A2 最新批次 |
| **910C** | 训练 + 推理（新一代） | 128GB | ~370-400 TFLOPS | ~500W | 下一代 Atlas |

## 推理卡 / 边缘

| SKU | 定位 | 显存（LPDDR） | INT8 算力 | TDP |
|---|---|---|---|---|
| **310P3** | 数据中心推理 | 24GB | ~140 TOPS | ~72W |
| **310P1** | 数据中心推理（入门） | 8GB | ~88 TOPS | ~67W |
| **310B** | 边缘推理 / 嵌入式 | 8-16GB | ~20 TOPS | ~20W |

## 多卡互联

- **910B 单机 8 卡**：HCCS / MESH 全互联；带宽 ~392 GB/s（每方向）
- **多机**：RoCE v2 over 200GbE，实际 ~150-180 Gb/s；需要正确 RANK_TABLE_FILE 和 HCCL_SOCKET_IFNAME
- **10 卡 / 12 卡模组**：Atlas 900 超节点集群（HCCS 跨机）

## 命令速查

```bash
# 查 NPU 列表 + 基本信息
npu-smi info

# 查单卡详情
npu-smi info -t board -i 0

# 查实时占用
npu-smi info watch -i 0 -d 1

# 查固件 / 驱动版本
npu-smi info -t board -i 0 | grep -E "Version|Firmware"
```

## 常见混淆

| 误解 | 澄清 |
|---|---|
| "910B = 910 的 B 批次" | 错。910B 是独立的新一代架构（达芬奇 V2），不是 910 的 rev |
| "910B 和 GPU A100 等价对比" | **算力侧** 910B 的 FP16 和 A100 差不多；**显存** 32/64GB 与 A100 80GB 差一档；**生态** 差距显著（少 CUDA） |
| "910B 能跑 CUDA" | **不能**。走 torch_npu / MindSpore 栈；CUDA 代码要迁移 |

## 相关

- `wiki/hardware/910b.md`
- `wiki/hardware/910c.md`
- `wiki/hardware/310p.md`
- `wiki/hardware/310b.md`
- `skill/ascend-troubleshoot/references/version_matrix.md`
