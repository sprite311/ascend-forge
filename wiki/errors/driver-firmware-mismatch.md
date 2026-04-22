---
id: driver-firmware-mismatch
title: 固件与驱动版本不匹配
kind: error
signature: "Can not find available NPU device"
aliases: ["ENV-001", "driver-firmware", "npu-device-not-found"]
tags: [environment, driver, firmware, installation, npu-smi]
related: [910b, 910c, 310p, 310b, cann]
stage: 安装
hardware: [910B, 910C, 310P, 310B]
status: stable
last_verified: 2026-04-20
sources:
  - skill/ascend-troubleshoot/references/knowledge_base.md#ENV-001
---

# 固件 / 驱动版本不匹配

## 症状
- `npu-smi info` 无法查到芯片
- `mindspore.run_check()` 报错
- `torch.npu.device_count()` 返回 0

## 报错示例

```
RuntimeError: Can not find available NPU device
```

## 根因
固件（firmware）和驱动（driver）**必须严格对应**；**且不同芯片型号有各自的驱动包，不可混用**。
常见错误：在 910B 上错装了 910C 的驱动包。

## 修复（标准流程）

### Step 1｜确认芯片型号
```bash
cat /usr/local/Ascend/driver/version.info
npu-smi info
# 或
lspci | grep -i "d801\|d802\|d500\|d100"   # 按型号过滤
```

### Step 2｜下载匹配驱动 + 固件
从昇腾社区按**芯片型号 + OS 架构**下载对应包：
https://www.hiascend.com/developer/download

### Step 3｜卸载旧驱动（⚠️ R020：生成命令，让用户执行）
```bash
/usr/local/Ascend/driver/script/uninstall.sh
```

### Step 4｜安装驱动（以 910B + aarch64 + 24.1.rc3 为例）
```bash
chmod +x Ascend-hdk-910b-npu-driver_24.1.rc3_linux-aarch64.run
./Ascend-hdk-910b-npu-driver_24.1.rc3_linux-aarch64.run --full
```

### Step 5｜安装固件
```bash
chmod +x Ascend-hdk-910b-npu-firmware_7.5.0.2.220.run
./Ascend-hdk-910b-npu-firmware_7.5.0.2.220.run --full
```

### Step 6｜重启后验证
```bash
reboot
# ...
npu-smi info      # 所有芯片 Health=OK
```

## 验证
```bash
npu-smi info
# 期望：每张卡的 Health=OK，Memory Usage 在合理范围（空载 ~ MB 级）
```

## 相关
- CANN 版本矩阵：[`wiki/software/cann.md`](../software/cann.md#硬件型号与-cann-版本)
- 三件套错配：[`wiki/errors/torch-npu-cann-version-mismatch.md`](torch-npu-cann-version-mismatch.md)
- 内核过低：`wiki/errors/kernel-too-old.md` *(Wave 2 待迁 · ENV-003)*

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-20: 迁入 from knowledge_base.md#ENV-001. source: case/2026-04-20-troubleshoot-migration-wave1
