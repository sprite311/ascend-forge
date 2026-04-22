---
id: general-debug
title: 昇腾通用排查流程（6 步）
kind: playbook
aliases: ["general-debug", "debug-playbook", "六步排查"]
tags: [debug, playbook, triage, ascend]
related: [cann, 910b, 310p, torch-npu, mindie]
status: stable
last_verified: 2026-04-20
sources:
  - skill/ascend-troubleshoot/references/general_debug.md
---

# 昇腾通用排查流程

> **使用场景**：任何昇腾相关报错的起点。先跑完这 6 步，再下钻到 `wiki/errors/<signature>.md`。
> **调用方式**：`@ascend-diagnoser` 的默认 SOP；用户也可手动跟跑。

---

## Step 1｜环境状态快速检查（30 秒）

```bash
# 1.1 驱动 / 固件
npu-smi info                                          # 所有 NPU 状态；Health=OK 说明底层活着
cat /usr/local/Ascend/driver/version.info             # 驱动版本

# 1.2 CANN 版本
cat /usr/local/Ascend/ascend-toolkit/latest/version.cfg

# 1.3 Python 三件套
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import torch_npu; print(f'torch_npu: {torch_npu.__version__}')"
python -c "import torch; print(f'NPU available: {torch.npu.is_available()}')"
python -c "import torch; print(f'NPU count: {torch.npu.device_count()}')"

# 1.4 OS
uname -r                                              # 内核（需 ≥ 4.19）
cat /etc/os-release
```

**判定**：
- `npu-smi info` 无输出 → [ENV-001 驱动/固件错配](../errors/driver-firmware-mismatch.md) 或容器问题 [CTR-001](../errors/docker-davinci-mount.md)
- `import torch_npu` 报错 → [DEP-001 三件套错配](../errors/torch-npu-cann-version-mismatch.md)
- `torch.npu.is_available()` 为 False → 同上

---

## Step 2｜按报错模式分类

| 错误模式                | 可能类别          | 先看                                                    |
|-------------------------|-------------------|---------------------------------------------------------|
| `No module named`       | 依赖 / 环境变量   | `pip list`, `source set_env.sh`                         |
| `Torch not compiled with CUDA` | CUDA 代码未迁移 | 搜 `.cuda()`；`wiki/errors/cuda-hardcoded.md` *(Wave 2 待迁 · MIG-001)* |
| `NPU out of memory`     | 显存不足 / 碎片   | [INF-003 碎片 OOM](../errors/npu-oom-fragmentation.md) · OOM-001 加载 OOM *(Wave 2 待迁)* |
| `HCCL error`            | 多卡通信          | [HCCL-001 残留进程](../errors/hccl-residual-process.md) / [HCCL-002 多机网络](../errors/hccl-multi-node-network.md) |
| `ACL error code:507018` | 推理随机采样      | [INF-001 507018](../errors/acl-507018.md)               |
| `ACL error code:107002` | 多线程 device 设置 | *(待迁)*                                                |
| `EZ/EE/EJ/EI/EP + 数字` | 昇腾底层错误码    | 看 Step 3 前缀表                                        |
| `Segfault / core dump`  | 版本错配 / 越界   | [DEP-001](../errors/torch-npu-cann-version-mismatch.md) |

---

## Step 3｜昇腾错误码前缀速查

| 前缀 | 含义            | 典型场景                    |
|------|-----------------|-----------------------------|
| EZ   | 运行时错误      | 算子执行、内存分配          |
| EE   | 参数校验错误    | 输入 shape / type 不匹配    |
| EJ   | 通信 / 集群错误 | HCCL 初始化、多卡通信       |
| EI   | 内部错误        | 一般需要升级 CANN           |
| EP   | 权限 / 资源错误 | 设备占用、权限不足          |

> 具体四位数错误码查**昇腾错误码手册**（见 [CANN 文档](https://www.hiascend.com/document)）。

---

## Step 4｜日志收集

```bash
# 开启详细日志
export ASCEND_GLOBAL_LOG_LEVEL=0      # 0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR
export ASCEND_SLOG_PRINT_TO_STDOUT=1  # 输出到终端

# 日志文件位置
ls /var/log/npu/slog/                 # 系统级
ls ~/ascend/log/                      # 用户级

# 完整诊断快照
npu-smi info -t usages                # NPU 利用率
npu-smi info -t memory                # 显存详情
npu-smi info -t temp                  # 温度
npu-smi info -t board -i 0            # 板级信息（含 AICore 数）
```

**打包**：将 Step 1 输出 + Step 4 日志打包成 `diagnostic-<date>.tar.gz`，便于复盘或提交官方 issue。

---

## Step 5｜常用修复动作（按副作用从小到大）

```bash
# 5.1 Python 进程级：清理显存缓存
python -c "import torch, torch_npu, gc; torch.npu.empty_cache(); gc.collect()"

# 5.2 进程级：杀残留（最常见问题，HCCL-001 必跑）
pkill -9 -f "torchrun|python.*train|mindie"
sleep 10

# 5.3 设备级：重置 NPU
for i in $(seq 0 7); do npu-smi set -t reset -i $i; done

# 5.4 驱动级：重新加载（不重启机器，谨慎）
# ⚠️ 需 root；有运行中任务会丢失
rmmod drv_pcie_host && modprobe drv_pcie_host && npu-smi info
```

> **安全护栏（R020）**：`rmmod` / `modprobe` / `npu-smi set reset` 属破坏性动作，Agent 不得自动执行，必须打印给用户确认。

---

## Step 6｜社区资源（直达）

| 资源                   | 地址                                                      | 适用场景               |
|------------------------|-----------------------------------------------------------|------------------------|
| 昇腾官方文档           | https://www.hiascend.com/document                         | 安装、API 参考         |
| 昇腾社区论坛           | https://www.hiascend.com/forum                            | 问答、经验分享         |
| Gitee CANN             | https://gitee.com/ascend/cann-community                   | Issue、算子样例        |
| LLaMA-Factory NPU 文档 | https://llamafactory.readthedocs.io/zh-cn/latest/advanced/npu.html | 训练框架适配         |
| 昇腾开源文档           | https://ascend.github.io/docs/                            | 开源项目文档           |
| ModelLink              | https://gitee.com/ascend/ModelLink                        | 模型适配参考实现       |

---

## 给 Agent 的使用提示

- **不得**在用户未给出报错的前提下直接跳到 Step 5（修复）——必须先 Step 1–4 定位。
- 每步的输出若命中已知 `wiki/errors/` 条目，直接引用并附"验证命令"给用户。
- Step 5 中的 5.3 / 5.4 必须**生成命令**给用户执行，Agent 自己不跑（R020）。

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-20: 初版。从 `skill/ascend-troubleshoot/references/general_debug.md` 迁入，补充错误签名 → `wiki/errors/` 链接；source: case/2026-04-20-troubleshoot-migration-wave1.
