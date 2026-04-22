#!/usr/bin/env bash
#
# run.sh — model-adaptation skill 的可执行入口
#
# SKILL.md 是 SOP 文档；本脚本把可自动化的部分自动化：
#   1) 环境体检（npu-smi / CANN / torch_npu 版本自检，对照版本矩阵）
#   2) 生成 HF→NPU eager load + 精度对齐的 Python 模板（拷到用户项目里填参）
#   3) 生成 GPU↔NPU 逐层 diff 模板（防 pitfall-rope-half-convention-mismatch）
#
# 用法：
#   skills/model-adaptation/run.sh env                       # 环境体检
#   skills/model-adaptation/run.sh template-load <OUT.py>    # 生成 load + smoke test 模板
#   skills/model-adaptation/run.sh template-diff <OUT.py>    # 生成逐层 diff 模板
#   skills/model-adaptation/run.sh --help
#
# 不做：
#   - 不自动下权重（路径太依赖客户环境）
#   - 不自动跑 generate（需要用户提供 GPU 基线做对比）
#   - 不改用户的 modeling_*.py（这是人工决策点）
#
# 相关：
#   - wiki/playbooks/hf-to-npu-7-step.md
#   - memory/pitfalls/pitfall-sdpa-not-implemented-on-npu.md
#   - memory/pitfalls/pitfall-rope-half-convention-mismatch.md
#   - memory/pitfalls/pitfall-dtype-mixing-bf16-fp16.md
#   - memory/facts/fact-torch-npu-version-matrix-25q1.md
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

env_check() {
    banner "Step 1 · 驱动 / 固件（npu-smi info）"
    if command -v npu-smi >/dev/null 2>&1; then
        npu-smi info 2>&1 | head -20 || echo "⚠️  npu-smi 存在但调用失败（可能非 NPU 机器）"
    else
        echo "❌ npu-smi 未找到——大概率不在 NPU 机器上。"
        echo "   这是 dry-run 友好，继续..."
    fi

    banner "Step 2 · CANN 版本"
    CANN_INFO="/usr/local/Ascend/ascend-toolkit/latest/aarch64-linux/ascend_toolkit_install.info"
    if [ -f "$CANN_INFO" ]; then
        cat "$CANN_INFO"
    else
        X86_INFO="/usr/local/Ascend/ascend-toolkit/latest/x86_64-linux/ascend_toolkit_install.info"
        if [ -f "$X86_INFO" ]; then
            cat "$X86_INFO"
        else
            echo "⚠️  CANN 未在 /usr/local/Ascend/ascend-toolkit/ 找到"
            echo "   记得 source /usr/local/Ascend/ascend-toolkit/set_env.sh"
        fi
    fi

    banner "Step 3 · torch + torch_npu 版本"
    python3 - <<'PY' 2>&1 || echo "⚠️  torch / torch_npu import 失败"
try:
    import torch
    print(f"torch: {torch.__version__}")
except Exception as e:
    print(f"❌ torch import 失败: {e}")
try:
    import torch_npu
    print(f"torch_npu: {torch_npu.__version__}")
    print(f"npu.is_available(): {torch.npu.is_available()}")
    print(f"npu.device_count(): {torch.npu.device_count()}")
except Exception as e:
    print(f"❌ torch_npu import 失败: {e}")
PY

    banner "Step 4 · 对照版本矩阵"
    echo "详细矩阵见："
    echo "  $REPO_ROOT/memory/facts/fact-torch-npu-version-matrix-25q1.md"
    echo ""
    echo "关键红线（训练期口径）："
    echo "  - torch 主版本必须 == torch_npu 主版本（2.1 ↔ 2.1.X，2.4 ↔ 2.4.X）"
    echo "  - driver ≥ firmware；反了就 NPU device not found"
    echo "  - CANN minor 版本变了大概率要重装 torch_npu"
}

template_load() {
    local out="${1:-model_adaptation_load.py}"
    if [ -z "${1:-}" ]; then
        echo "❌ 需要输出路径：$0 template-load <OUT.py>" >&2
        exit 2
    fi
    if [ -e "$out" ]; then
        echo "❌ $out 已存在，拒绝覆盖。换个路径。" >&2
        exit 2
    fi
    cat > "$out" <<'PY'
"""
model_adaptation_load.py — HF 模型 → NPU eager load + smoke test 模板
由 skills/model-adaptation/run.sh template-load 生成

填完 TODO 后跑：  python3 model_adaptation_load.py

参考：
  wiki/playbooks/hf-to-npu-7-step.md  Step 3 + Step 4
  memory/pitfalls/pitfall-sdpa-not-implemented-on-npu.md
  memory/pitfalls/pitfall-dtype-mixing-bf16-fp16.md
"""
import torch
import torch_npu  # noqa: F401  ← 必须 import，激活 NPU backend
from transformers import AutoModelForCausalLM, AutoTokenizer

# TODO 1：改成你的权重路径
MODEL_PATH = "/weights/Qwen2-7B-Instruct"

# TODO 2：910B/C 首选 BF16；老 910 / 310P 可用 FP16（二选一，别混）
DTYPE = torch.bfloat16

# TODO 3：验证 prompt。随便选，但要和 GPU baseline 跑的是同一个
PROMPT = "The capital of France is"


def main():
    print(f"▶ loading {MODEL_PATH} in {DTYPE} with eager attention...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=DTYPE,
        attn_implementation="eager",   # 首次必用 eager，避开 SDPA 未实现
        trust_remote_code=True,
    ).npu().eval()
    print(f"  ✅ load ok. dtype={model.dtype}, device={next(model.parameters()).device}")

    # dtype 健康检查（防 pitfall-dtype-mixing-bf16-fp16）
    bad = []
    for name, p in model.named_parameters():
        if p.dtype not in (DTYPE, torch.float32):
            bad.append(f"{name}: {p.dtype}")
    if bad:
        print(f"  ⚠️  检测到 {len(bad)} 个参数 dtype 不一致（示例）：")
        for line in bad[:5]:
            print(f"     {line}")
    else:
        print(f"  ✅ dtype 健康：全 {DTYPE} 或 FP32")

    print(f"\n▶ smoke test: greedy decode 20 tokens")
    torch.manual_seed(42)
    inputs = tokenizer(PROMPT, return_tensors="pt").to("npu")
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=20, do_sample=False)
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"  prompt: {PROMPT!r}")
    print(f"  output: {text!r}")
    print()
    print("▶ 下一步：")
    print("  - 把 output 和 GPU baseline 的前 20 token 对一下")
    print("  - 完全一致 → 走 Step 5 FA fusion")
    print("  - 有偏差 → 跑 template-diff 生成逐层 diff 脚本定位")


if __name__ == "__main__":
    main()
PY
    chmod +x "$out"
    echo "✅ 模板已写到：$out"
    echo ""
    echo "下一步："
    echo "  1. 改顶部 3 个 TODO"
    echo "  2. python3 $out"
    echo "  3. 对比 GPU 基线输出"
}

template_diff() {
    local out="${1:-precision_diff.py}"
    if [ -z "${1:-}" ]; then
        echo "❌ 需要输出路径：$0 template-diff <OUT.py>" >&2
        exit 2
    fi
    if [ -e "$out" ]; then
        echo "❌ $out 已存在，拒绝覆盖。换个路径。" >&2
        exit 2
    fi
    cat > "$out" <<'PY'
"""
precision_diff.py — GPU ↔ NPU 逐层 forward diff 模板
由 skills/model-adaptation/run.sh template-diff 生成

用途：
  当 NPU 上 generate 出来的 token 和 GPU 不一致、但 loss 看起来正常时，
  这是定位 RoPE / attention / norm 哪一层先发散的唯一靠谱方法。
  （详见 memory/pitfalls/pitfall-rope-half-convention-mismatch.md 的"策略 A"）

用法：
  1. 在 GPU 机器上跑一次，保存每层 hidden_state → gpu_hidden_states.pt
  2. 在 NPU 机器上跑一次，保存每层 hidden_state → npu_hidden_states.pt
  3. 在任一机器上对比：python3 precision_diff.py

依赖：
  - 两份 .pt 文件都是 dict: {layer_name: tensor}
  - shape 一致；tensor 可以在任意 device（脚本自动搬 CPU）
"""
import os
import sys
import torch

# TODO 1：改为你的 dump 文件路径
GPU_DUMP = "gpu_hidden_states.pt"
NPU_DUMP = "npu_hidden_states.pt"

# TODO 2：阈值。max-diff 1e-2 一般是 FA/RoPE 级的发散
MAX_DIFF_THRESHOLD = 1e-2
COSINE_THRESHOLD = 0.999


def load(path: str) -> dict:
    if not os.path.exists(path):
        print(f"❌ {path} 不存在。先在对应机器上 dump。")
        sys.exit(2)
    data = torch.load(path, map_location="cpu")
    assert isinstance(data, dict), f"{path} 应是 dict[str, Tensor]"
    return data


def cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    a = a.float().flatten()
    b = b.float().flatten()
    return torch.nn.functional.cosine_similarity(a, b, dim=0).item()


def main():
    gpu = load(GPU_DUMP)
    npu = load(NPU_DUMP)

    common = sorted(set(gpu) & set(npu))
    only_gpu = set(gpu) - set(npu)
    only_npu = set(npu) - set(gpu)
    if only_gpu:
        print(f"⚠️  only in GPU dump: {sorted(only_gpu)[:3]}...")
    if only_npu:
        print(f"⚠️  only in NPU dump: {sorted(only_npu)[:3]}...")

    print(f"{'layer':<40} {'max_diff':>12} {'cosine':>10} {'verdict':>8}")
    print("-" * 75)

    first_bad = None
    for name in common:
        g, n = gpu[name].float(), npu[name].float()
        if g.shape != n.shape:
            print(f"{name:<40} {'SHAPE MISMATCH':>24} {str(g.shape)} vs {str(n.shape)}")
            continue
        diff = (g - n).abs().max().item()
        cos = cosine(g, n)
        verdict = "OK"
        if diff > MAX_DIFF_THRESHOLD or cos < COSINE_THRESHOLD:
            verdict = "❌ BAD"
            if first_bad is None:
                first_bad = name
        print(f"{name:<40} {diff:>12.4e} {cos:>10.4f} {verdict:>8}")

    print()
    if first_bad:
        print(f"▶ 第一个发散的层：{first_bad}")
        print("  → 大概率原因按优先级：")
        print("    1. 如果层名含 'rotary' / 'rope' → pitfall-rope-half-convention-mismatch")
        print("    2. 如果层名含 'attn' / 'attention' → pitfall-sdpa-not-implemented-on-npu 或 FA 实现差异")
        print("    3. 如果层名含 'norm' → dtype 混用（pitfall-dtype-mixing-bf16-fp16）")
        print("    4. 前几层就差 → tokenizer / embedding / dtype 整体错了")
        sys.exit(1)
    else:
        print("✅ 全层 max_diff ≤ {MAX_DIFF_THRESHOLD:.0e}，cosine ≥ {COSINE_THRESHOLD}。NPU / GPU 精度对齐 ok。".format(**{"MAX_DIFF_THRESHOLD": MAX_DIFF_THRESHOLD, "COSINE_THRESHOLD": COSINE_THRESHOLD}))


if __name__ == "__main__":
    main()
PY
    chmod +x "$out"
    echo "✅ 模板已写到：$out"
    echo ""
    echo "下一步（两台机器配合）："
    echo "  GPU 机：在 modeling_*.py 里加 hook 存 hidden_state → gpu_hidden_states.pt"
    echo "  NPU 机：同样 hook 存 → npu_hidden_states.pt"
    echo "  然后跑：python3 $out"
}

MODE="${1:-help}"
shift || true

case "$MODE" in
    env)
        env_check
        ;;
    template-load)
        template_load "${1:-}"
        ;;
    template-diff)
        template_diff "${1:-}"
        ;;
    --help|-h|help|"")
        usage
        ;;
    *)
        echo "unknown mode: $MODE" >&2
        usage
        exit 1
        ;;
esac
