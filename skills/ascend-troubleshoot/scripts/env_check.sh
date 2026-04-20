#!/bin/bash
# env_check.sh - 昇腾 NPU 环境自检脚本
# 用法: bash env_check.sh
# 输出: 环境状态报告，标记 PASS / WARN / FAIL

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }

echo "============================================"
echo "  昇腾 NPU 环境自检报告"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# === 1. 操作系统 ===
echo "--- 操作系统 ---"
OS_NAME=$(cat /etc/os-release 2>/dev/null | grep "^PRETTY_NAME" | cut -d'"' -f2 || echo "未知")
echo "  系统: $OS_NAME"

KERNEL=$(uname -r)
KERNEL_MAJOR=$(echo "$KERNEL" | cut -d'.' -f1)
KERNEL_MINOR=$(echo "$KERNEL" | cut -d'.' -f2)
echo "  内核: $KERNEL"

if [ "$KERNEL_MAJOR" -gt 4 ] || ([ "$KERNEL_MAJOR" -eq 4 ] && [ "$KERNEL_MINOR" -ge 19 ]); then
    pass "内核版本 >= 4.19"
else
    fail "内核版本 < 4.19，昇腾驱动要求 >= 4.19"
fi

ARCH=$(uname -m)
echo "  架构: $ARCH"

# === 2. NPU 驱动 ===
echo ""
echo "--- NPU 驱动 ---"
if command -v npu-smi &>/dev/null; then
    pass "npu-smi 命令可用"
    
    NPU_COUNT=$(npu-smi info -l 2>/dev/null | grep "Total Count" | awk '{print $NF}' || echo "0")
    if [ "$NPU_COUNT" -gt 0 ] 2>/dev/null; then
        pass "检测到 $NPU_COUNT 张 NPU"
    else
        # 尝试另一种方式获取
        NPU_COUNT=$(npu-smi info 2>/dev/null | grep -c "NPU ID" || echo "0")
        if [ "$NPU_COUNT" -gt 0 ]; then
            pass "检测到 $NPU_COUNT 张 NPU"
        else
            fail "未检测到 NPU 设备"
        fi
    fi
    
    # 检查设备健康状态
    UNHEALTHY=$(npu-smi info 2>/dev/null | grep -i "fault\|error\|abnormal" || true)
    if [ -z "$UNHEALTHY" ]; then
        pass "NPU 设备状态正常"
    else
        warn "检测到异常设备状态: $UNHEALTHY"
    fi
else
    fail "npu-smi 命令不可用，驱动可能未安装"
fi

# 驱动版本
DRIVER_VER_FILE="/usr/local/Ascend/driver/version.info"
if [ -f "$DRIVER_VER_FILE" ]; then
    DRIVER_VER=$(cat "$DRIVER_VER_FILE" | head -1)
    echo "  驱动版本: $DRIVER_VER"
else
    warn "无法获取驱动版本信息"
fi

# === 3. CANN ===
echo ""
echo "--- CANN Toolkit ---"
CANN_VER_FILE="/usr/local/Ascend/ascend-toolkit/latest/version.cfg"
if [ -f "$CANN_VER_FILE" ]; then
    CANN_VER=$(cat "$CANN_VER_FILE" | head -1)
    echo "  CANN 版本: $CANN_VER"
    pass "CANN Toolkit 已安装"
else
    # 尝试其他路径
    CANN_ALT=$(find /usr/local/Ascend -name "version.cfg" 2>/dev/null | head -1)
    if [ -n "$CANN_ALT" ]; then
        CANN_VER=$(cat "$CANN_ALT" | head -1)
        echo "  CANN 版本: $CANN_VER (路径: $CANN_ALT)"
        pass "CANN Toolkit 已安装（非标准路径）"
    else
        fail "CANN Toolkit 未安装或路径异常"
    fi
fi

# 检查环境变量
if [ -n "$ASCEND_HOME_PATH" ]; then
    pass "ASCEND_HOME_PATH 已设置: $ASCEND_HOME_PATH"
else
    warn "ASCEND_HOME_PATH 未设置，请 source set_env.sh"
fi

if echo "$LD_LIBRARY_PATH" | grep -qi "ascend"; then
    pass "LD_LIBRARY_PATH 包含 Ascend 路径"
else
    warn "LD_LIBRARY_PATH 未包含 Ascend 路径"
fi

# === 4. Python 环境 ===
echo ""
echo "--- Python 环境 ---"
PYTHON_VER=$(python3 --version 2>/dev/null || python --version 2>/dev/null || echo "未找到")
echo "  Python: $PYTHON_VER"

# torch
TORCH_VER=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo "未安装")
echo "  PyTorch: $TORCH_VER"
if [ "$TORCH_VER" != "未安装" ]; then
    pass "PyTorch 已安装"
else
    fail "PyTorch 未安装"
fi

# torch_npu
TORCH_NPU_VER=$(python3 -c "import torch_npu; print(torch_npu.__version__)" 2>/dev/null || echo "未安装")
echo "  torch_npu: $TORCH_NPU_VER"
if [ "$TORCH_NPU_VER" != "未安装" ]; then
    pass "torch_npu 已安装"
    
    # 检查版本是否匹配
    TORCH_MAJOR=$(echo "$TORCH_VER" | cut -d'.' -f1-2)
    NPU_MAJOR=$(echo "$TORCH_NPU_VER" | cut -d'.' -f1-2)
    if [ "$TORCH_MAJOR" = "$NPU_MAJOR" ]; then
        pass "torch 和 torch_npu 版本匹配 ($TORCH_MAJOR)"
    else
        fail "torch ($TORCH_MAJOR) 和 torch_npu ($NPU_MAJOR) 版本不匹配！"
    fi
else
    fail "torch_npu 未安装"
fi

# NPU 可用性
NPU_AVAIL=$(python3 -c "import torch; import torch_npu; print(torch.npu.is_available())" 2>/dev/null || echo "False")
if [ "$NPU_AVAIL" = "True" ]; then
    pass "NPU 设备可用 (torch.npu.is_available() = True)"
    
    DEVICE_COUNT=$(python3 -c "import torch; import torch_npu; print(torch.npu.device_count())" 2>/dev/null || echo "0")
    echo "  可用 NPU 数量: $DEVICE_COUNT"
else
    fail "NPU 设备不可用 (torch.npu.is_available() = False)"
fi

# === 5. 容器检测 ===
echo ""
echo "--- 容器环境 ---"
if [ -f "/.dockerenv" ] || grep -q "docker\|containerd" /proc/1/cgroup 2>/dev/null; then
    echo "  运行环境: Docker 容器"
    
    # 检查设备挂载
    DAVINCI_COUNT=$(ls /dev/davinci* 2>/dev/null | wc -l)
    if [ "$DAVINCI_COUNT" -gt 0 ]; then
        pass "检测到 $DAVINCI_COUNT 个 davinci 设备节点"
    else
        fail "未检测到 davinci 设备节点，容器启动时需 --device 挂载"
    fi
    
    # 检查共享内存
    SHM_SIZE=$(df -h /dev/shm 2>/dev/null | tail -1 | awk '{print $2}')
    echo "  共享内存大小: $SHM_SIZE"
    SHM_BYTES=$(df /dev/shm 2>/dev/null | tail -1 | awk '{print $2}')
    if [ "$SHM_BYTES" -lt 67108864 ] 2>/dev/null; then  # < 64GB
        warn "共享内存较小 ($SHM_SIZE)，大模型推理建议 --shm-size=1000g"
    else
        pass "共享内存大小足够"
    fi
else
    echo "  运行环境: 裸机（非容器）"
fi

# === 6. 关键依赖 ===
echo ""
echo "--- 关键依赖库 ---"
DEPS="numpy scipy protobuf sympy cffi decorator pyyaml attrs psutil"
MISSING=""
for dep in $DEPS; do
    if python3 -c "import $dep" 2>/dev/null; then
        true  # 静默通过
    else
        MISSING="$MISSING $dep"
    fi
done

if [ -z "$MISSING" ]; then
    pass "所有关键依赖库已安装"
else
    warn "缺失依赖库:$MISSING"
    echo "  安装命令: pip install$MISSING"
fi

# === 汇总 ===
echo ""
echo "============================================"
echo "  自检完成"
echo "============================================"
echo ""
echo "如有 FAIL 项，请参考故障排查库中对应的解决方案。"
echo "如有 WARN 项，建议尽快修复以避免潜在问题。"
