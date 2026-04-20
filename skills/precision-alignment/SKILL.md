---
name: precision-alignment
description: 适配 / 量化 / 优化后，与 GPU/FP32 基线做精度对齐
trigger: ["精度", "对齐", "diff", "logits", "nan", "cosine"]
applies_to:
  hardware: [910B, 310P]
  software: [torch_npu, mindspore]
version: 0.1.0
owners: [ascend-adapter, ascend-diagnoser]
safety: read-write
---

# 精度对齐 SOP

## 基本思路

"先整体，再逐层，再逐算子"。发现 diff 位置即收敛到最小重现。

## 步骤

1. **固定条件**：seed、输入（tokens 或 tensor）、dtype（先 FP32，再 FP16/BF16）、batch_size=1
2. **端到端对比**：生成 logits 或 loss，与 GPU 基线逐元素 `cosine`、`max_abs`、`max_rel`
   - 阈值建议：cosine ≥ 0.999, max_abs ≤ 1e-3（FP16）
3. **逐层 hook**：PyTorch `register_forward_hook`、MindSpore `ms.nn.Cell.register_forward_pre_hook`
4. **Dump 对比**：
   - torch: `torch.save(tensor, "layer_X.pt")`
   - MindSpore: `ms.save_checkpoint(...)` 或自定义 numpy dump
   - 对比脚本模板见 `skills/precision-alignment/examples/compare.py`（可自建）
5. **定位到算子**：
   - 常见嫌疑：attention（softmax 数值稳定性）、norm（eps 差异）、rope（精度）、量化算子
6. **修复策略**：
   - 精度敏感层强制 FP32
   - 替换为昇腾已认证的融合实现
   - 必要时打开 `torch_npu.npu.config.allow_internal_format=False`

## 工具命令（示意）

```bash
python compare.py --golden ./gpu_dump --candidate ./npu_dump --report ./report.md
```

## 失败回流

- 已定位到算子 → `wiki/operators/<op>.md#precision`
- 已定位到某模型架构 → `wiki/models/<id>.md#precision-notes`
- 通用经验 → `memory/lessons/`

## 参考

- 官方昇腾精度对齐工具（`msit` / `ait`）
