---
id: hccl-residual-process
title: "HCCL 初始化失败 · 上次训练进程残留 (EJ0001)"
kind: error
signature: "EJ0001: Failed to initialize the HCCP process"
aliases: ["HCCL-001", "EJ0001", "hccl-residual", "hccl-init-failed"]
tags: [training, hccl, distributed, EJ, ej0001, residual-process]
related: [910b, 910c, torch-npu, mindformers]
stage: 训练
hardware: [910B, 910C]
status: stable
last_verified: 2026-04-20
sources:
  - skill/ascend-troubleshoot/references/knowledge_base.md#HCCL-001
---

# HCCL 初始化失败 · 上次训练进程残留

## 症状
多卡训练启动时 HCCL 初始化失败；第一条错误栈来自 `torch_npu/csrc/distributed/ProcessGroupHCCL.cpp`；
错误码 **EJ0001**，提示 "Maybe the last training process is running"。

## 报错示例

```
RuntimeError: [ERROR] HCCL error in: torch_npu/csrc/distributed/ProcessGroupHCCL.cpp:64
ERR02200 DIST call hccl api failed.
EJ0001: Failed to initialize the HCCP process.
Reason: Maybe the last training process is running.
```

## 根因
上次训练异常退出后，`python / torchrun / mindie` 等进程**未被彻底清理**，
占用着 NPU 设备；新进程的 HCCL `init_pg` 无法获取设备句柄。

## 修复

### Step 1｜查残留
```bash
ps aux | grep -E "python|torch|mindie" | grep -v grep
```

### Step 2｜杀残留（⚠️ R020：生成命令让用户执行）
```bash
pkill -9 -f "torchrun|python.*train|mindie"
sleep 10
```

### Step 3｜若设备仍未释放，重置 NPU（⚠️ 破坏性）
```bash
# 单卡
npu-smi set -t reset -i 0
# 所有 8 卡
for i in $(seq 0 7); do npu-smi set -t reset -i $i; done
```

### Step 4｜确认显存已释放
```bash
npu-smi info
# 所有卡的 Memory Usage 应接近 0
```

## 验证
```bash
# 重跑训练；HCCL init 成功、所有 rank 出现在日志前 10 行
torchrun --nproc_per_node=8 train.py 2>&1 | head -50
```

## 相关
- 多机训练网络问题：[`wiki/errors/hccl-multi-node-network.md`](hccl-multi-node-network.md)
- Playbook Step 5.2：[`wiki/playbooks/general-debug.md`](../playbooks/general-debug.md#step-5常用修复动作按副作用从小到大)

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-20: 迁入 from knowledge_base.md#HCCL-001. source: case/2026-04-20-troubleshoot-migration-wave1
