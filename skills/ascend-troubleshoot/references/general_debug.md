# 通用排查流程与诊断命令

## 第一步：环境状态快速检查

```bash
# 1. 驱动和固件
npu-smi info                          # 查看所有 NPU 状态
cat /usr/local/Ascend/driver/version.info  # 驱动版本

# 2. CANN 版本
cat /usr/local/Ascend/ascend-toolkit/latest/version.cfg

# 3. Python 环境
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import torch_npu; print(f'torch_npu: {torch_npu.__version__}')"
python -c "import torch; print(f'NPU available: {torch.npu.is_available()}')"
python -c "import torch; print(f'NPU count: {torch.npu.device_count()}')"

# 4. 操作系统
uname -r                              # 内核版本
cat /etc/os-release                    # 发行版信息
```

## 第二步：根据报错分类

| 错误模式               | 可能的问题类别       | 首先检查            |
|----------------------|-------------------|-------------------|
| `No module named`     | 依赖缺失/环境变量    | pip list, set_env.sh |
| `CUDA enabled`        | CUDA 代码未迁移     | 搜索 .cuda() 调用   |
| `NPU out of memory`   | 显存不足           | 模型大小 vs 显存     |
| `HCCL error`          | 多卡通信问题        | 残留进程、网络配置    |
| `ACL error code:XXXX` | 算子/运行时问题     | 按错误码查文档       |
| `EZ/EE/EJ + 数字`     | 昇腾底层错误码      | 昇腾错误码手册       |
| `Segfault`            | 版本不匹配/内存越界  | 三件套版本对应        |
| `507018`              | 随机采样不兼容      | 设置 do_sample=False |
| `107002`              | 设备访问错误        | 多线程 device 设置   |

## 第三步：昇腾错误码前缀含义

| 前缀 | 含义             | 典型场景              |
|------|-----------------|---------------------|
| EZ   | 运行时错误        | 算子执行、内存分配      |
| EE   | 参数校验错误      | 输入 shape/type 不匹配 |
| EJ   | 通信/集群错误     | HCCL 初始化、多卡通信   |
| EI   | 内部错误          | 一般需要升级 CANN      |
| EP   | 权限/资源错误     | 设备占用、权限不足      |

## 第四步：日志收集

```bash
# 开启详细日志
export ASCEND_GLOBAL_LOG_LEVEL=0       # 0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR
export ASCEND_SLOG_PRINT_TO_STDOUT=1   # 输出到终端

# 日志文件位置
ls /var/log/npu/slog/                  # 系统级日志
ls ~/ascend/log/                       # 用户级日志

# 收集完整诊断信息
npu-smi info -t usages                 # NPU 使用率
npu-smi info -t memory                 # 显存详情
npu-smi info -t temp                   # 温度
```

## 第五步：常用修复动作

```bash
# 重置 NPU（解决设备卡死）
for i in $(seq 0 7); do npu-smi set -t reset -i $i; done

# 杀掉残留进程
pkill -9 -f "torchrun|python.*train|mindie"
sleep 10

# 重新加载驱动（不重启机器）
rmmod drv_pcie_host
modprobe drv_pcie_host
npu-smi info

# 清理 NPU 显存缓存（Python 中）
import torch
torch.npu.empty_cache()
import gc
gc.collect()
```

## 第六步：社区资源

| 资源 | 地址 | 适用场景 |
|------|------|---------|
| 昇腾官方文档 | https://www.hiascend.com/document | 安装、API 参考 |
| 昇腾社区论坛 | https://www.hiascend.com/forum | 问答、经验分享 |
| Gitee CANN | https://gitee.com/ascend/cann-community | Issue、算子样例 |
| LLaMA-Factory NPU 文档 | https://llamafactory.readthedocs.io/zh-cn/latest/advanced/npu.html | 训练框架适配 |
| 昇腾开源文档 | https://ascend.github.io/docs/ | 开源项目文档 |
| ModelLink | https://gitee.com/ascend/ModelLink | 模型适配参考实现 |
