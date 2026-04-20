---
name: operator-replacement
description: 原框架算子在昇腾缺失 / 低效时的替换方案查找与落地
trigger: ["算子", "operator", "not implemented", "aten::"]
applies_to:
  hardware: [910B, 310P]
version: 0.1.0
owners: [ascend-adapter, ascend-tuner]
safety: read-write
---

# 算子替换 SOP

## 何时使用
- 跑 forward 报 `RuntimeError: ... is not implemented for device: privateuseone`（torch_npu）
- 某算子在 MindSpore 没对应 Cell
- 算子能跑但性能差（tuner 场景）

## 步骤

1. **记录算子签名**：名字、输入 shape/dtype、batch/seq context
2. **查 `wiki/operators/<op>.md`** —— 有方案直接用
3. **未登记**，依次尝试：
   - 官方 ATB（Ascend Transformer Boost）是否有融合实现
   - `torch_npu.contrib` 扩展
   - MindFormers / MindSpore 已有同义算子
   - 自己组合基础算子（把复杂算子拆成 matmul + add + ...）
   - **最后手段**：AscendC / TBE 手写（成本高，仅在瓶颈算子）
4. **落地**：
   - 加 monkey-patch / hook 替换
   - 写单算子 unit test（shape 覆盖 + 精度阈值）
5. **回灌知识**：创建或更新 `wiki/operators/<op>.md`，含：
   - 原定义（简要）
   - 昇腾替换方案（含代码片段）
   - 精度差异（与 GPU 对比）
   - 性能数据（可选）
   - 相关模型（哪些模型用了这个算子）

## 常见算子（初始）
- RMSNorm → ATB 融合版
- RoPE → ATB 融合版
- FlashAttention → ATB FA / PA
- SwiGLU → 组合实现
- 分组 GEMM（MoE） → ATB GroupedMatmul

## 参考
- ATB 算子库文档
- `wiki/operators/`
