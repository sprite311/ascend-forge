---
id: cann
title: CANN (Compute Architecture for Neural Networks)
kind: software
aliases: ["CANN", "cann-toolkit", "ascend-toolkit"]
tags: [runtime, toolkit, ascend]
related: [910b, 310p, mindie, mindspore, torch-npu, mindformers]
status: stable
last_verified: 2026-04-20
sources:
  - https://www.hiascend.com/software/cann
---

# CANN

## 概览
昇腾基础软件栈，包含 runtime、算子库（AICPU / AICore）、ATC 模型转换、调试工具（msprof 等）。
所有上层框架（MindSpore、torch_npu、MindIE、MindFormers）都依赖 CANN。

## 环境变量（高频）
```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
# 关键变量
# ASCEND_HOME, ASCEND_OPP_PATH, LD_LIBRARY_PATH
```

## 版本矩阵（模板，值待补）
| CANN | 驱动 | 910B | 310P | MindIE | torch_npu | MindSpore |
|---|---|---|---|---|---|---|
| 8.0.0 | ≥ 23.0.rc3 | ✅ | ✅ | 1.0.x | 2.1.x / 2.3.x | 2.3.x |
| 7.0.x | ≥ 23.0.0 | ✅ | ✅ | 0.9.x | 2.1.x | 2.2.x |

> 首次使用者请用 `cat /usr/local/Ascend/.../version.cfg` 核实本环境版本，对照
> 官方 release note 更新本表，并刷新 `last_verified`。

## 安装要点
- 顺序：驱动 → 固件 → CANN runtime → CANN toolkit → 上层框架
- 卸载前务必 `source set_env.sh` 以保证路径正确

## 常见坑
_尚未记录。由 `ascend-env-doctor` 按场景追加。_

## 相关算子 / 相关模型
_由 wiki link checker 自动维护。_

## Backlinks
<!-- auto -->

## Changelog
- 2026-04-20: 种子页创建，版本矩阵为模板值，**需用户按实际环境核实**。
