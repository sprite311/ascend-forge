#!/usr/bin/env bash
#
# run.sh — vllm-ascend-serving skill 的可执行入口
#
# SKILL.md 是 SOP；本脚本做参数校验 + 显存预算估算 + 启动命令生成，
# 专治 pitfall-block-size-alignment（默认 16 直接崩）和 vllm-kv-cache-alloc-failed。
#
# 用法：
#   skills/vllm-ascend-serving/run.sh check --model /weights/Qwen2-7B --tp 1 --max-len 32768 --block-size 128
#   skills/vllm-ascend-serving/run.sh estimate --params 7 --kv-seq 32768 --batch 8 --tp 1 --hbm 32
#   skills/vllm-ascend-serving/run.sh gen-cmd --model /weights/Qwen2-7B --tp 1 --max-len 32768 --block-size 128
#   skills/vllm-ascend-serving/run.sh --help
#
# 故意不做：
#   - 不真 pip install vllm-ascend（环境假设前置）
#   - 不直接启动服务（用 gen-cmd，用户自己 paste 运行；留出人工 review 窗口）
#
# 相关：
#   - wiki/software/vllm-ascend.md
#   - memory/pitfalls/pitfall-block-size-alignment.md
#   - wiki/errors/vllm-kv-cache-alloc-failed.md
#   - wiki/errors/npu-oom-fragmentation.md
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

banner() {
    echo ""
    echo "━━━ $1 ━━━"
}

usage() {
    grep '^#' "$0" | sed 's/^# \?//'
}

# ---- 参数解析（简单 kv） ----
declare -A ARGS
parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --model)       ARGS[model]="$2"; shift 2 ;;
            --tp)          ARGS[tp]="$2"; shift 2 ;;
            --max-len)     ARGS[max_len]="$2"; shift 2 ;;
            --block-size)  ARGS[block_size]="$2"; shift 2 ;;
            --mem-util)    ARGS[mem_util]="$2"; shift 2 ;;
            --port)        ARGS[port]="$2"; shift 2 ;;
            --params)      ARGS[params]="$2"; shift 2 ;;
            --kv-seq)      ARGS[kv_seq]="$2"; shift 2 ;;
            --batch)       ARGS[batch]="$2"; shift 2 ;;
            --hbm)         ARGS[hbm]="$2"; shift 2 ;;
            --dtype)       ARGS[dtype]="$2"; shift 2 ;;
            *)             echo "未知参数: $1" >&2; exit 2 ;;
        esac
    done
}

# ---- 子命令：check ----
do_check() {
    parse_args "$@"
    local fail=0

    banner "check · 参数合法性"

    # 1. model 路径
    if [ -z "${ARGS[model]:-}" ]; then
        echo "  ❌ --model 必填"
        fail=1
    elif [ ! -e "${ARGS[model]}" ]; then
        echo "  ⚠️  --model ${ARGS[model]} 在当前机器不存在（若是远程路径可忽略）"
    else
        echo "  ✅ --model ${ARGS[model]}"
    fi

    # 2. block-size —— pitfall-block-size-alignment
    local bs="${ARGS[block_size]:-128}"
    if [ "$bs" != "64" ] && [ "$bs" != "128" ]; then
        echo "  ❌ --block-size=$bs  非法（昇腾上必须 64 或 128；默认 16 直接崩）"
        echo "     见 memory/pitfalls/pitfall-block-size-alignment.md"
        fail=1
    else
        echo "  ✅ --block-size $bs"
    fi

    # 3. tp 必须 ≥1
    local tp="${ARGS[tp]:-1}"
    if ! [[ "$tp" =~ ^[0-9]+$ ]] || [ "$tp" -lt 1 ]; then
        echo "  ❌ --tp=$tp  非法"
        fail=1
    else
        echo "  ✅ --tp $tp"
    fi

    # 4. max-len 必须 > block-size
    local ml="${ARGS[max_len]:-4096}"
    if [ "$ml" -le "$bs" ]; then
        echo "  ❌ --max-len ($ml) 必须 > --block-size ($bs)"
        fail=1
    else
        echo "  ✅ --max-len $ml"
    fi

    # 5. mem-util 范围
    local mu="${ARGS[mem_util]:-0.85}"
    case "$mu" in
        0.[0-9]|0.[0-9][0-9])
            echo "  ✅ --mem-util $mu"
            ;;
        *)
            echo "  ⚠️  --mem-util=$mu  建议 0.80-0.90（太高易碎片 OOM）"
            ;;
    esac

    echo ""
    if [ "$fail" -eq 1 ]; then
        echo "❌ 校验失败；参数修正后再跑 gen-cmd"
        exit 1
    fi
    echo "✅ 校验通过"
}

# ---- 子命令：estimate ----
do_estimate() {
    parse_args "$@"
    banner "estimate · 粗估 KV cache + 权重显存"
    python3 - <<PY
params_b = float("${ARGS[params]:-7}")    # B 参数
kv_seq   = int("${ARGS[kv_seq]:-4096}")
batch    = int("${ARGS[batch]:-8}")
tp       = int("${ARGS[tp]:-1}")
hbm_gb   = float("${ARGS[hbm]:-32}")       # 单卡 HBM
dtype    = "${ARGS[dtype]:-bf16}"
bytes_per = {"bf16":2,"fp16":2,"fp32":4,"w8a8":1,"w4":0.5}.get(dtype, 2)

# 简化公式
weight_gb = params_b * bytes_per                 # 全模型权重
weight_per_card = weight_gb / tp

# KV cache: 2（K,V）× layers × kv_heads × head_dim × seq × batch × bytes
# 粗估 layers×kv_heads×head_dim ≈ hidden_size × 2（KV 对），用 scaling 法
# 假设 7B hidden=4096 layers=32 → KV per token per layer ≈ 2*4096*2=16KB bf16
# → per seq per batch ≈ 16KB * 32 * 4096 = 2GB 左右
# 这里用 scaling：kv_gb_per_token ≈ 0.00005 * params_b  (经验值，量纲 GB/token)
kv_per_token_gb = 0.00005 * params_b
kv_total_gb = kv_per_token_gb * kv_seq * batch

per_card = weight_per_card + kv_total_gb / tp
util = per_card / hbm_gb * 100

print(f"  模型参数       : {params_b} B")
print(f"  dtype          : {dtype} ({bytes_per} B/param)")
print(f"  权重（全模型）  : {weight_gb:.1f} GB")
print(f"  权重 / 卡       : {weight_per_card:.1f} GB （tp={tp}）")
print(f"  KV / token     : {kv_per_token_gb*1024:.2f} MB")
print(f"  KV 合计        : {kv_total_gb:.1f} GB （seq={kv_seq}, batch={batch}）")
print(f"  单卡占用估算   : {per_card:.1f} GB / {hbm_gb:.0f} GB = {util:.0f}%")
print()
if util > 90:
    print("  🔴 估算占用 > 90%，实测必 OOM。建议降 batch / 降 seq / 增 TP")
elif util > 75:
    print("  🟡 估算占用 > 75%，刚好；长跑碎片化后易 OOM")
else:
    print("  🟢 预算健康（此为粗估；真机以 vllm 启动后 npu-smi 为准）")
PY
}

# ---- 子命令：gen-cmd ----
do_gen_cmd() {
    parse_args "$@"

    local model="${ARGS[model]:-/weights/YOUR_MODEL}"
    local tp="${ARGS[tp]:-1}"
    local ml="${ARGS[max_len]:-32768}"
    local bs="${ARGS[block_size]:-128}"
    local mu="${ARGS[mem_util]:-0.85}"
    local port="${ARGS[port]:-8000}"

    # 内嵌 check
    if [ "$bs" != "64" ] && [ "$bs" != "128" ]; then
        echo "❌ --block-size=$bs 非法（必须 64 / 128）" >&2
        exit 2
    fi

    banner "gen-cmd · 启动命令"
    cat <<CMD
# --- 确保环境已 source ---
source /usr/local/Ascend/ascend-toolkit/set_env.sh

# --- 启动命令 ---
python -m vllm.entrypoints.openai.api_server \\
  --model $model \\
  --device npu \\
  --tensor-parallel-size $tp \\
  --max-model-len $ml \\
  --block-size $bs \\
  --gpu-memory-utilization $mu \\
  --port $port

# --- 验证（另开 terminal）---
curl http://localhost:$port/v1/models
curl http://localhost:$port/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{"model":"$(basename $model)","messages":[{"role":"user","content":"hi"}]}'
CMD
    echo ""
    echo "已 paste 到上方；人工 review 后复制运行。"
}

MODE="${1:-help}"
shift || true

case "$MODE" in
    check)     do_check "$@" ;;
    estimate)  do_estimate "$@" ;;
    gen-cmd)   do_gen_cmd "$@" ;;
    --help|-h|help|"") usage ;;
    *)
        echo "unknown mode: $MODE" >&2
        usage
        exit 1
        ;;
esac
