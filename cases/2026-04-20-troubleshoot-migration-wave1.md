---
id: 2026-04-20-troubleshoot-migration-wave1
date: 2026-04-20
duration_min: 18
subagents: [knowledge-curator]
models: []
hardware: [910B, 910C, 310P, 310B]
software: [cann, torch-npu, vllm-ascend, mindie, hccl]
outcome: resolved
tags: [migration, wave1, knowledge-base, wiki-seed, troubleshoot, content-backfill]
extracted:
  memory:
    - lesson-seed-page-must-link-errors
    - fact-ascend-three-piece-matrix
    - pitfall-block-size-alignment
  wiki:
    - software/cann.md (fill matrices)
    - playbooks/general-debug.md (new)
    - errors/acl-507018.md (new)
    - errors/vllm-kv-cache-alloc-failed.md (new)
    - errors/npu-oom-fragmentation.md (new)
    - errors/hccl-residual-process.md (new)
    - errors/hccl-multi-node-network.md (new)
    - errors/driver-firmware-mismatch.md (new)
    - errors/docker-davinci-mount.md (new)
    - errors/torch-npu-cann-version-mismatch.md (new)
  rules: []
---

## 问题
**骨架阶段交付了设计 + 目录，但真实用户可用性低**——
8 个 wiki 种子页 7 个为 `TBD`；用户已提交的 917 行结构化故障库 `skill/ascend-troubleshoot/references/knowledge_base.md`
没有进入 wiki 知识网络，导致"agent 诊断能力 ≠ 用户已有的文字知识"。

本 case 执行 **Wave 1 内容迁移**：把用户的 skill references → wiki（错误签名页、通用 playbook、软件版本矩阵）
按昇腾知识模型的 schema 落位。

## 过程（时间线）
- **00:00** 读 `skill/ascend-troubleshoot/references/{general_debug.md, version_matrix.md, knowledge_base.md}` 全量。
- **00:02** 把 `version_matrix.md` 的 4 张表（核心三件套 / OS / 硬件×CANN / 框架兼容）合并进 `wiki/software/cann.md`，`status: stable`，`last_verified: 2026-04-20`，`source: skill/...#version_matrix.md`。
- **00:05** 把 `general_debug.md` 的 6 步流程迁为 `wiki/playbooks/general-debug.md`，每步末尾加"命中则跳 `wiki/errors/` 对应页"的链接。
- **00:08** 按**高频 / 高阻塞**原则从 11 类 × ~25 条中挑 8 条迁入 `wiki/errors/`：
  - 推理三件套：`acl-507018`, `vllm-kv-cache-alloc-failed`, `npu-oom-fragmentation`
  - HCCL 两件套：`hccl-residual-process`, `hccl-multi-node-network`
  - 环境三件套：`driver-firmware-mismatch`, `docker-davinci-mount`, `torch-npu-cann-version-mismatch`
- **00:15** 更新 `wiki/INDEX.md` 注册新页；标出 Wave 2+ 剩余 15 条迁移清单。
- **00:17** Curator 抽取 memory + 本 case。
- **00:18** 链接完整性 / 策略检查（下一条 validation 待跑）。

## 迁移映射表（source → target）

| Source (skill/ascend-troubleshoot) | Target (wiki)                                              | Kind     |
|------------------------------------|-------------------------------------------------------------|----------|
| `references/version_matrix.md` (全文) | `wiki/software/cann.md` 版本矩阵 / OS / 硬件 / 框架兼容 4 张表 | software |
| `references/general_debug.md` (全文) | `wiki/playbooks/general-debug.md`                          | playbook |
| `knowledge_base.md#INF-001`        | `wiki/errors/acl-507018.md`                                 | error    |
| `knowledge_base.md#INF-002`        | `wiki/errors/vllm-kv-cache-alloc-failed.md`                 | error    |
| `knowledge_base.md#INF-003`        | `wiki/errors/npu-oom-fragmentation.md`                      | error    |
| `knowledge_base.md#HCCL-001`       | `wiki/errors/hccl-residual-process.md`                      | error    |
| `knowledge_base.md#HCCL-002`       | `wiki/errors/hccl-multi-node-network.md`                    | error    |
| `knowledge_base.md#ENV-001`        | `wiki/errors/driver-firmware-mismatch.md`                   | error    |
| `knowledge_base.md#CTR-001(+CTR-002)` | `wiki/errors/docker-davinci-mount.md`（合并子项）          | error    |
| `knowledge_base.md#DEP-001(+DEP-002)` | `wiki/errors/torch-npu-cann-version-mismatch.md`（合并子项）| error    |

## 根因（本次暴露的真问题）
之前只写了架构和空壳页，没把已有的 **917 行用户资产**接入 wiki 网络——造成"agent 诊断力 ≠ 用户已有知识"。
Wave 1 只覆盖高频 8 条；剩余 15 条分 Wave 2+ 迁。

## 修复
见 "过程" + "迁移映射表"。全部写入路径合规（`wiki/`），遵守 R011（追加式，不覆盖原 skill 文件）。

## 复盘
- **做得好**：按 wiki schema（签名 / 根因 / 修复 / 验证 / 相关 / Changelog）统一格式；`related:` 字段形成 errors ↔ software ↔ playbook 双向网络；合并 ENV-001 + CTR-001+CTR-002 + DEP-001+DEP-002 等**同场景子项**到一页，避免碎片。
- **可以更好**：部分相关链接指向尚未迁移的 `*(待迁)*` 页——链接完整性检查会标红，计 Wave 2 补上。可以考虑让 curator 自动在 Wave 2 迁移完成后批量清理 `*(待迁)*` 标记。

## Metrics
- 工具调用数: ~18（Read × 5, Write × 10, Edit × 2, Bash × 1）
- 失败重试数: 0
- 总耗时 (min): ~18
- 新增 wiki 页: 9（8 errors + 1 playbook）
- 修改 wiki 页: 2（cann.md、INDEX.md）
- 新增 memory: 3（lesson + fact + pitfall）
- 新增 rule proposal: 0
- 新增 case: 1（本文件）

## Curator Log
- wrote: `wiki/playbooks/general-debug.md`
- wrote: `wiki/errors/acl-507018.md`
- wrote: `wiki/errors/vllm-kv-cache-alloc-failed.md`
- wrote: `wiki/errors/npu-oom-fragmentation.md`
- wrote: `wiki/errors/hccl-residual-process.md`
- wrote: `wiki/errors/hccl-multi-node-network.md`
- wrote: `wiki/errors/driver-firmware-mismatch.md`
- wrote: `wiki/errors/docker-davinci-mount.md`
- wrote: `wiki/errors/torch-npu-cann-version-mismatch.md`
- wrote: `wiki/hardware/910c.md`（validation 阶段为修复 `related:910c` 创建的 stub，status=draft）
- wrote: `wiki/hardware/310b.md`（同上，status=draft）
- wrote: `memory/facts/fact-ascend-three-piece-matrix.md`
- wrote: `memory/lessons/lesson-seed-page-must-link-errors.md`
- wrote: `memory/pitfalls/pitfall-block-size-alignment.md`
- appended: `memory/INDEX.md`（facts + lessons + pitfalls 三个小节）
- appended: `wiki/software/cann.md`（Changelog + 3 张真实矩阵 + 常见坑链接）
- appended: `wiki/INDEX.md`（errors 表格 + playbook 小节 + Wave 2 计划注释）
