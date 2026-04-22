---
id: docker-davinci-mount
title: Docker 容器内无法访问 NPU 设备（davinci 挂载）
kind: error
signature: "No such file or directory: '/dev/davinci0'"
aliases: ["CTR-001", "davinci-mount", "container-no-npu", "docker-npu"]
tags: [container, docker, davinci, device-mount, shm-size]
related: [910b, 910c, 310p, cann]
stage: 环境
hardware: [全部]
status: stable
last_verified: 2026-04-20
sources:
  - skill/ascend-troubleshoot/references/knowledge_base.md#CTR-001
---

# Docker 容器内无法访问 NPU

## 症状
- 容器内 `npu-smi info` 无输出
- 启动推理 / 训练时找不到 `/dev/davinci0`

## 报错示例

```
RuntimeError: Can not find available NPU device
# 或
No such file or directory: '/dev/davinci0'
```

## 根因
Docker 默认**不透传宿主设备节点**。昇腾 NPU 需显式挂载：
- 卡设备：`/dev/davinci0` .. `/dev/davinci7`
- 管理节点：`/dev/davinci_manager`、`/dev/hisi_hdc`、`/dev/devmm_svm`
- 驱动 / CANN：`/usr/local/Ascend`

此外 `--shm-size` 过小会在大模型场景下 Bus error（见下方"共享内存不足"）。

## 修复

### 完整启动命令（8 卡）

```bash
docker run -itd \
  --privileged \
  --name ascend-dev \
  --net=host \
  --shm-size=1000g \
  --device=/dev/davinci0 \
  --device=/dev/davinci1 \
  --device=/dev/davinci2 \
  --device=/dev/davinci3 \
  --device=/dev/davinci4 \
  --device=/dev/davinci5 \
  --device=/dev/davinci6 \
  --device=/dev/davinci7 \
  --device=/dev/davinci_manager \
  --device=/dev/hisi_hdc \
  --device=/dev/devmm_svm \
  -v /usr/local/Ascend:/usr/local/Ascend \
  -v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi \
  your-image:tag bash
```

### 关键注意
- `--privileged` 必需
- `--shm-size` ≥ 64g，大模型推理建议 **1000g**（否则 IPC 队列崩）
- 三个管理设备 (`davinci_manager`, `hisi_hdc`, `devmm_svm`) 都必须挂
- `/usr/local/Ascend` 必须挂（包含驱动和 CANN）

### 共享内存不足（CTR-002 常见连带问题）

```
RuntimeError: unable to open shared memory object
# 或
Bus error (core dumped)
```

修复：`--shm-size=1000g` 启动；或运行中临时扩（重启失效）：

```bash
mount -o remount,size=100G /dev/shm
```

## 验证
```bash
docker exec -it ascend-dev bash -c 'npu-smi info && df -h /dev/shm'
# 期望：所有卡显示；/dev/shm 足够大
```

## 相关
- 驱动 / 固件问题（宿主就起不来）：[`wiki/errors/driver-firmware-mismatch.md`](driver-firmware-mismatch.md)
- CANN 挂载 / 环境变量：[`wiki/software/cann.md`](../software/cann.md#环境变量高频)

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-20: 迁入 from knowledge_base.md#CTR-001（含 CTR-002 shm 子项）. source: case/2026-04-20-troubleshoot-migration-wave1
