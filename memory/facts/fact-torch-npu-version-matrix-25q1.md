---
id: fact-torch-npu-version-matrix-25q1
date: 2026-04-22
tags: [version, torch, torch-npu, cann, python, compat-matrix, ascend-910b]
status: active
source: training-knowledge-cutoff-2025-05
ttl_days: 180
verified_at: 2026-04-22
---

# 事实：torch × torch_npu × CANN × Python 版本配对（2025Q1 截止期公开稳定组合）

> **source**: training-knowledge-cutoff-2025-05
> **ttl_days: 180**（短 TTL）——此类组合表每个 CANN 季度 drop 都会新增一列，必须定期 reverify。

昇腾 **torch_npu** 的严格版本耦合：错一档会 segfault / import 崩 / API 不匹配。下表是**截止 2025-05 公开可见的稳定组合**：

| CANN | driver/firmware | torch | torch_npu | Python | OS（推荐） |
|---|---|---|---|---|---|
| 7.0.RC1 | 23.0.rc3 | 2.1.0 | 2.1.0.post3 | 3.8 / 3.9 | openEuler 22.03 / Ubuntu 20.04 |
| 7.0.0 | 23.0.0 | 2.1.0 | 2.1.0.post6 | 3.9 / 3.10 | openEuler 22.03 / Ubuntu 22.04 |
| 7.1.RC1 | 24.0.rc1 | 2.1.0 / 2.2.0 | 2.1.0.post7 / 2.2.0.rc1 | 3.9 / 3.10 | openEuler 22.03 / Ubuntu 22.04 |
| 8.0.RC1 | 24.1.rc1 | 2.2.0 / 2.4.0 | 2.2.0.post1 / 2.4.0.rc1 | 3.9 / 3.10 | openEuler 22.03 |
| 8.0.RC2 | 24.1.rc2 | 2.4.0 | 2.4.0.post1 | 3.10 | openEuler 22.03 / 24.03 |
| 8.0.0 | 24.1.0 | 2.4.0 / 2.5.0 | 2.4.0.post2 / 2.5.0.rc1 | 3.10 / 3.11 | openEuler 24.03 / Ubuntu 24.04 |

## 关键约束

1. **三片耦合**：`torch` 主版本 = `torch_npu` 主版本（2.1 ↔ 2.1.X，2.4 ↔ 2.4.X），**跨主版本 100% 崩**
2. **Python 11+ 需检查**：Ubuntu 24 / openEuler 24 默认带 py3.11+，某些 torch_npu 二进制没出 3.11 轮子，要用 conda 装 3.10
3. **driver ≥ firmware**：driver 版本必须 ≥ firmware，反了就 `NPU device not found`
4. **检查三行命令**：
   ```bash
   # driver/firmware
   npu-smi info
   # CANN
   cat /usr/local/Ascend/ascend-toolkit/latest/aarch64-linux/ascend_toolkit_install.info
   # torch_npu
   python -c "import torch_npu; print(torch_npu.__version__)"
   ```

## 版本跳跃的建议路径

- **升级前**：保留老环境 snapshot（conda env export；最好 docker image tag）
- **升级顺序**：先 driver/firmware → 再 CANN → 再 torch_npu（反过来 90% 翻车）
- **验证**：`python -c "import torch; import torch_npu; x = torch.randn(2).npu(); print(x)"` 跑通才算成功

## 来源

- `skill/ascend-troubleshoot/references/version_matrix.md`（同仓已有）
- 昇腾官方 CANN release notes（2024 各季度）
- HuaweiAscend GitHub torch_npu README

## 反链

- `wiki/software/cann.md`
- `wiki/software/torch-npu.md`
- `wiki/errors/torch-npu-cann-version-mismatch.md`
- `memory/facts/fact-ascend-three-piece-matrix.md`（本条是其具体版本数据）
