#!/usr/bin/env bash
#
# run.sh — precision-alignment skill 的可执行入口
#
# SKILL.md 里的 "先整体，再逐层，再逐算子" 三步都可以脚本化：
#   1) gen-hook <OUT.py>       生成 register_forward_hook 注入 + dump 模板
#   2) gen-compare <OUT.py>    生成 logits / per-layer 对比脚本
#   3) run-compare <gpu.pt> <npu.pt>   直接跑 compare（依赖 torch；无 torch 则报错退出）
#   4) --help
#
# "首日别跳精度对齐" —— 见 wiki/playbooks/hf-to-npu-7-step.md Step 4。
# 同 skills/model-adaptation/run.sh template-diff 的兄弟脚本，此处更专注 hook 注入。
#
# 相关：
#   - memory/pitfalls/pitfall-rope-half-convention-mismatch.md
#   - memory/pitfalls/pitfall-dtype-mixing-bf16-fp16.md
#   - memory/pitfalls/pitfall-sdpa-not-implemented-on-npu.md
#
set -euo pipefail

banner() { echo ""; echo "━━━ $1 ━━━"; }
usage() { grep '^#' "$0" | sed 's/^# \?//'; }

# ---- gen-hook ----
gen_hook() {
    local out="${1:-}"
    if [ -z "$out" ]; then echo "需要 OUT.py" >&2; exit 2; fi
    if [ -e "$out" ]; then echo "❌ $out 已存在" >&2; exit 2; fi
    cat > "$out" <<'PY'
"""
hook_dump.py — 给 HF 模型注入 forward hook，dump 每层输出
由 skills/precision-alignment/run.sh gen-hook 生成

跑一遍 GPU，一遍 NPU：
    python3 hook_dump.py --device cuda --out gpu_states.pt
    python3 hook_dump.py --device npu  --out npu_states.pt
然后用 skills/precision-alignment/run.sh run-compare gpu_states.pt npu_states.pt
"""
import argparse
import torch

# 可选 import torch_npu；GPU 机上没装也无所谓
try:
    import torch_npu  # noqa: F401
except ImportError:
    pass

from transformers import AutoModelForCausalLM, AutoTokenizer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="/weights/Qwen2-7B-Instruct")
    ap.add_argument("--device", choices=["cuda", "npu", "cpu"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt", default="The capital of France is")
    ap.add_argument("--dtype", default="bfloat16", choices=["bfloat16", "float16", "float32"])
    ap.add_argument("--layers", type=int, default=-1,
                    help="dump 前 N 层；-1 = 全部（首轮建议 5-10 层足够定位）")
    args = ap.parse_args()

    dtype = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}[args.dtype]

    print(f"▶ load {args.model} → {args.device} ({args.dtype})")
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        attn_implementation="eager",    # 对齐阶段必用 eager
        trust_remote_code=True,
    ).to(args.device).eval()

    dump = {}

    def make_hook(name):
        def hook(_module, _input, output):
            # output 可能是 tensor 或 tuple(tensor, ...)
            t = output[0] if isinstance(output, tuple) else output
            dump[name] = t.detach().to("cpu").float()   # 统一 FP32 存，方便对齐
        return hook

    handles = []
    count = 0
    for name, module in model.named_modules():
        if name == "":
            continue
        # 挑 "有意义" 的层：transformer block 级 + 内部 attn / mlp / norm
        parts = name.split(".")
        # 只 hook 层叶子节点 + 一些 block 级名字
        if any(kw in name for kw in ("rotary", "q_proj", "k_proj", "o_proj",
                                      "input_layernorm", "post_attention_layernorm",
                                      "mlp.down_proj", "self_attn")):
            handles.append(module.register_forward_hook(make_hook(name)))
            count += 1
            if args.layers > 0 and count >= args.layers:
                break
    print(f"  registered {count} hooks")

    torch.manual_seed(42)
    inputs = tok(args.prompt, return_tensors="pt").to(args.device)
    with torch.no_grad():
        _ = model(**inputs)

    for h in handles:
        h.remove()

    torch.save(dump, args.out)
    print(f"  dumped {len(dump)} layers → {args.out}")


if __name__ == "__main__":
    main()
PY
    chmod +x "$out"
    echo "✅ 写到 $out"
    echo ""
    echo "下一步："
    echo "  GPU 机：python3 $out --device cuda --out gpu_states.pt --model <path>"
    echo "  NPU 机：python3 $out --device npu  --out npu_states.pt --model <path>"
    echo "  然后：  $0 run-compare gpu_states.pt npu_states.pt"
}

# ---- gen-compare ----
gen_compare() {
    local out="${1:-}"
    if [ -z "$out" ]; then echo "需要 OUT.py" >&2; exit 2; fi
    if [ -e "$out" ]; then echo "❌ $out 已存在" >&2; exit 2; fi
    cat > "$out" <<'PY'
"""
compare.py — 逐层 max_diff / cosine 对比 + 第一发散层诊断
由 skills/precision-alignment/run.sh gen-compare 生成
"""
import argparse
import torch

MAX_DIFF_OK = 1e-2
COS_OK = 0.999


def cosine(a, b):
    a = a.flatten().float()
    b = b.flatten().float()
    return torch.nn.functional.cosine_similarity(a, b, dim=0).item()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", required=True)
    ap.add_argument("--npu", required=True)
    ap.add_argument("--max-diff", type=float, default=MAX_DIFF_OK)
    ap.add_argument("--cosine", type=float, default=COS_OK)
    args = ap.parse_args()

    gpu = torch.load(args.gpu, map_location="cpu")
    npu = torch.load(args.npu, map_location="cpu")
    common = sorted(set(gpu) & set(npu))

    print(f"{'layer':<50} {'max_diff':>12} {'cosine':>10} {'':>6}")
    print("-" * 82)

    first_bad = None
    for name in common:
        g, n = gpu[name].float(), npu[name].float()
        if g.shape != n.shape:
            print(f"{name:<50} SHAPE MISMATCH {g.shape} vs {n.shape}")
            continue
        d = (g - n).abs().max().item()
        c = cosine(g, n)
        verdict = "OK" if d <= args.max_diff and c >= args.cosine else "❌"
        print(f"{name:<50} {d:>12.4e} {c:>10.4f} {verdict:>6}")
        if verdict != "OK" and first_bad is None:
            first_bad = (name, d, c)

    print()
    if first_bad:
        name, d, c = first_bad
        print(f"▶ 第一发散层：{name}  (max_diff={d:.3e}, cosine={c:.4f})")
        print("  诊断提示：")
        lname = name.lower()
        if "rotary" in lname or "rope" in lname:
            print("    → 疑似 pitfall-rope-half-convention-mismatch (Neox vs GPT-NeoX)")
        elif "q_proj" in lname or "k_proj" in lname or "self_attn" in lname:
            print("    → 疑似 attention 实现差异（SDPA / FA fallback）")
            print("      先换 attn_implementation='eager' 排除 SDPA")
        elif "norm" in lname:
            print("    → 疑似 dtype 混用（pitfall-dtype-mixing-bf16-fp16）或 eps 差异")
        elif "mlp" in lname:
            print("    → 疑似 SiLU/GELU 数值差 或 dtype 问题")
        else:
            print("    → 先查：dtype 是否一致 / attn_implementation 是否相同")
        raise SystemExit(1)
    print("✅ 全层对齐。")


if __name__ == "__main__":
    main()
PY
    chmod +x "$out"
    echo "✅ 写到 $out"
}

# ---- run-compare (直接跑) ----
run_compare() {
    local gpu="${1:-}"
    local npu="${2:-}"
    if [ -z "$gpu" ] || [ -z "$npu" ]; then
        echo "用法：$0 run-compare <gpu.pt> <npu.pt>" >&2
        exit 2
    fi
    if ! python3 -c "import torch" 2>/dev/null; then
        echo "❌ 当前环境没装 torch。先装 torch 再跑 run-compare，或用 gen-compare 生成脚本跑别的机器。" >&2
        exit 2
    fi
    python3 - "$gpu" "$npu" <<'PY'
import sys, torch
gpu_path, npu_path = sys.argv[1], sys.argv[2]
gpu = torch.load(gpu_path, map_location="cpu")
npu = torch.load(npu_path, map_location="cpu")
common = sorted(set(gpu) & set(npu))
def cosine(a,b):
    a=a.flatten().float(); b=b.flatten().float()
    return torch.nn.functional.cosine_similarity(a,b,dim=0).item()
print(f"{'layer':<50} {'max_diff':>12} {'cosine':>10}  ")
print("-"*82)
first_bad=None
for name in common:
    g,n = gpu[name].float(), npu[name].float()
    if g.shape!=n.shape: continue
    d=(g-n).abs().max().item(); c=cosine(g,n)
    v = "OK" if d<=1e-2 and c>=0.999 else "❌"
    print(f"{name:<50} {d:>12.4e} {c:>10.4f} {v:>6}")
    if v!="OK" and first_bad is None: first_bad=name
print()
if first_bad:
    print(f"▶ 第一发散：{first_bad}")
    sys.exit(1)
else:
    print("✅ 对齐")
PY
}

MODE="${1:-help}"; shift || true
case "$MODE" in
    gen-hook)     gen_hook "${1:-}" ;;
    gen-compare)  gen_compare "${1:-}" ;;
    run-compare)  run_compare "${1:-}" "${2:-}" ;;
    --help|-h|help|"") usage ;;
    *) echo "unknown mode: $MODE" >&2; usage; exit 1 ;;
esac
