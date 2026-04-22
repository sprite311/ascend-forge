---
id: mindspore
title: MindSpore
kind: software
aliases: ["MindSpore", "mindspore", "ms"]
tags: [framework, ascend, training, inference, static-graph, jit]
related: [cann, mindformers, 910b, 910c]
status: stable
last_verified: 2026-04-20
sources:
  - https://www.mindspore.cn
  - https://gitee.com/mindspore/mindspore
---

# MindSpore

## 概览
华为**自研深度学习框架**。与 PyTorch / TensorFlow 并列，针对昇腾做深度优化：
- **图模式 (Graph Mode)** — 默认静态图，完整图编译 + 算子融合，性能优势最大
- **PyNative Mode** — 动态图，Debug 友好
- **jit 装饰器** — 局部 JIT，写 PyTorch 风格代码但享受图编译收益

## 版本

| MindSpore | CANN    | Python  | 备注 |
|-----------|---------|---------|------|
| 2.3.x     | 8.0.0+  | 3.8-3.11 | 当前主推，图模式稳定  |
| 2.2.x     | 7.0.x+  | 3.8-3.10 | 兼容维护             |

详：[`cann.md`](cann.md#硬件型号与-cann-版本)

## 安装

```bash
# 910B + aarch64 + CANN 8.0.0 场景示例
pip install mindspore==2.3.1

# 验证
python -c "import mindspore; print(mindspore.__version__)"
python -c "import mindspore; mindspore.run_check()"
# 期望：MindSpore version xxx; The result of mindspore.run_check: ...
```

## 上层框架
- **MindFormers** — HuggingFace 风格的模型训推库（基于 MS）
- **MindSpore Lite** — 端侧 / 边缘推理
- **MindSpeed** — 大模型并行训练加速
- **MindIE** — 推理引擎，与 MS 栈集成度最高

## 关键要点（迁移 / 调试）

### 图模式 vs 动态图
```python
import mindspore as ms
ms.set_context(mode=ms.GRAPH_MODE)    # 默认，推荐生产
ms.set_context(mode=ms.PYNATIVE_MODE) # 仅调试用
```

### jit_level（图优化级别）
```python
ms.set_context(jit_level="O2")   # O0 / O1 / O2，生产建议 O2
```

### 常见坑
- **静态图 Python 控制流限制**：`if cond: ...` 中 `cond` 不能是动态 tensor 值，改 `ops.where` 或 `ms.jit` 外层处理
- **Tensor vs Parameter**：训练参数必须是 `ms.Parameter`，普通 `Tensor` 无梯度
- **run_check 失败**：多半是 CANN 版本或驱动问题（见 [driver-firmware-mismatch](../errors/driver-firmware-mismatch.md)）

## 相关
- 训练框架：[`mindformers.md`](mindformers.md)
- 运行时：[`cann.md`](cann.md)
- 推理引擎：[`mindie.md`](mindie.md)

## Backlinks
<!-- auto -->
- [910b](../hardware/910b.md)
- [910c](../hardware/910c.md)
- [cann](cann.md)
- [mindformers](mindformers.md)

## Changelog
- 2026-04-20: Wave 2 填充——补版本矩阵、图模式、jit_level、静态图常见坑。source: case/2026-04-20-wave2-seed-pages
- 2026-04-20: 占位创建。
