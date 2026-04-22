#!/usr/bin/env python3
"""
路由回归基准（Ascend-Forge bench）。

输入：`bench/golden-questions.yaml` 里的 N 条黄金题。
过程：每条按"关键词加权"算一次主 subagent 路由决策，与 expected_subagent 对比。
输出：pass/fail 报告 + 混淆矩阵 + 失败题逐条解释。

与 `@subagent-X` 真实触发的差异说明：
  真实 agent 会加载 CLAUDE.md 路由表 + LLM 语义理解，本 bench 只用关键词近似。
  目的是：给 CLAUDE.md 路由表 / subagent 描述 *以及 tools/bench.py 里的 KEYWORDS 表本身*
  做**回归**——任何一方改动后要能 ≥90% 正确。

用法：
  python3 tools/bench.py                                 # 全量
  python3 tools/bench.py --id q10-acl-507018             # 单题
  python3 tools/bench.py --category diagnosis            # 按类跑
  python3 tools/bench.py --json > bench/last-run.json    # 机器可读

依赖：仅 stdlib；YAML 用内置行扫描 parser（见 `parse_yaml_simple`）。
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ─── 关键词路由表（bench 本身的路由近似） ─────────────────────────────────────
# 改动这里就要重跑 bench 看回归；改动 CLAUDE.md 也要同步改这里。
# 权重：主词 3，辅助词 1。
KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "ascend-adapter": [
        ("迁移", 3), ("migrate", 3), ("port", 2), ("HuggingFace", 3), ("transformers", 2),
        ("torch_npu", 2), ("MindSpore", 2), ("转换", 2),
        ("算子", 3), ("operator", 3), ("替换", 2), ("精度", 3), ("loss", 2),
        ("对齐", 2), ("adapt", 2),
    ],
    "ascend-deployer": [
        ("部署", 3), ("deploy", 3), ("serve", 3), ("启动", 2), ("start", 1),
        ("MindIE", 3), ("vLLM", 3), ("vllm-ascend", 3), ("MindFormers", 3),
        ("OpenAI", 2), ("接口", 2), ("API", 2),
        # 注：不要加裸"服务"——它在问题文本里常作背景噪音（如"推理服务出了 OOM"其实是诊断题）。
        # 只保留语义更窄的"推理服务"。
        ("推理服务", 2), ("多机", 3), ("多卡", 2), ("分布式", 2),
        ("ranktable", 3),
    ],
    "ascend-tuner": [
        ("调优", 3), ("tune", 2), ("性能", 2), ("perf", 2),
        ("显存", 2), ("吞吐", 2), ("时延", 2), ("latency", 2), ("throughput", 2),
        ("profile", 3), ("profiling", 3), ("msprof", 3),
        ("量化", 3), ("W8A8", 3), ("W4A16", 3), ("SmoothQuant", 3), ("quant", 2),
        ("block-size", 3), ("max-total-tokens", 3),
        ("KV", 2), ("PagedAttention", 2), ("瓶颈", 2), ("优化", 1),
        # Wave 6.1 补：LLM-serving perf 的通用术语（非为具体题目定制，是 tuner 领域本身的词）
        ("decode", 2), ("prefill", 2), ("tokens/s", 2),
        ("batch-size", 2), ("batching", 2), ("并发", 2), ("concurrency", 2),
        ("慢", 1), ("加速", 2), ("提速", 2),
        # 语气词 '调' 单字：权重很低，只在平手时加分
        ("调", 1),
    ],
    "ascend-diagnoser": [
        ("报错", 3), ("error", 2), ("错误", 2), ("bug", 2), ("崩", 2), ("fail", 2),
        ("ACL", 3), ("HCCL", 2), ("超时", 2), ("timeout", 2),
        ("OOM", 3), ("诊断", 3), ("troubleshoot", 3), ("精度", 2), ("定位", 2),
        ("查", 1), ("为啥", 1), ("怎么回事", 2),
    ],
    "ascend-env-doctor": [
        ("驱动", 3), ("driver", 3), ("固件", 3), ("firmware", 3),
        ("CANN", 3), ("npu-smi", 3), ("装", 2), ("install", 2),
        ("环境", 2), ("硬件", 2), ("版本", 2), ("version mismatch", 3),
        ("三件套", 3),
    ],
    "ascend-benchmarker": [
        ("基准", 3), ("benchmark", 3), ("baseline", 3), ("基线", 3),
        ("吞吐对比", 3), ("性能基线", 3), ("回归对比", 2), ("对比", 2), ("compare", 2),
        ("跑基准", 3),
        # Wave 6.1 补：基准评测的标准语汇
        ("MMLU", 3), ("CEval", 3), ("HumanEval", 3), ("GSM8K", 3),
        ("评测", 2), ("eval", 2), ("evaluation", 2), ("精度保持", 3),
    ],
}


# ─── 轻量 YAML parser（仅支持本 bench 的 schema） ───────────────────────────

def parse_yaml_simple(text: str) -> dict:
    """
    极简 parser，仅支持：
      - 顶层 'key:' 后跟 block list of mappings
      - item mapping 里 scalar 值（字符串、数字）或 inline list [a, b]
    不支持通用 YAML；够本 bench 用即可。
    """
    out: dict = {"questions": []}
    cur: dict | None = None
    pending_list_key: str | None = None
    in_questions = False

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        # 顶层 'questions:'
        if raw.startswith("questions:"):
            in_questions = True
            continue
        if not in_questions:
            continue
        # 新 item: '  - id: ...'
        m = re.match(r"^\s*-\s+([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if m:
            # 开始新 item
            if cur is not None:
                out["questions"].append(cur)
            cur = {}
            k, v = m.group(1), m.group(2).strip()
            cur[k] = _parse_scalar(v)
            pending_list_key = None
            continue
        # 缩进的 'key: value'
        m2 = re.match(r"^\s{4,}([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if m2 and cur is not None:
            k, v = m2.group(1), m2.group(2).strip()
            cur[k] = _parse_scalar(v)
            pending_list_key = None
            continue
    if cur is not None:
        out["questions"].append(cur)
    return out


def _parse_scalar(v: str):
    if v == "":
        return ""
    # inline list
    if v.startswith("[") and v.endswith("]"):
        items = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
        return items
    # quoted
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    # bare scalar
    return v


# ─── 路由器 ───────────────────────────────────────────────────────────────

def classify(question: str) -> tuple[str, dict[str, int]]:
    scores: dict[str, int] = {}
    for agent, keys in KEYWORDS.items():
        s = 0
        for kw, w in keys:
            if re.search(re.escape(kw), question, re.IGNORECASE):
                s += w
        scores[agent] = s
    if all(v == 0 for v in scores.values()):
        return ("NO_MATCH", scores)
    winner = max(scores, key=scores.get)  # type: ignore[arg-type]
    return (winner, scores)


# ─── Runner ──────────────────────────────────────────────────────────────

def run(questions: list[dict], filter_id: str | None, filter_category: str | None) -> list[dict]:
    results = []
    for q in questions:
        if filter_id and q.get("id") != filter_id:
            continue
        if filter_category and q.get("category") != filter_category:
            continue
        if not q.get("question"):
            continue
        predicted, scores = classify(q["question"])
        expected = q.get("expected_subagent", "")
        passed = predicted == expected
        # score gap = winner - runner-up
        sorted_scores = sorted(scores.values(), reverse=True)
        gap = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]
        results.append({
            "id": q.get("id"),
            "question": q.get("question"),
            "expected": expected,
            "predicted": predicted,
            "pass": passed,
            "confidence_gap": gap,
            "scores": scores,
            "category": q.get("category"),
            "difficulty": q.get("difficulty"),
        })
    return results


def print_report(results: list[dict]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    rate = 100.0 * passed / total if total else 0.0

    print(f"\n=== Ascend-Forge 路由 Bench 报告 ===")
    print(f"  共 {total} 题  ·  通过 {passed}  ·  通过率 {rate:.1f}%")
    print(f"  {'✅ PASS' if rate >= 90 else '❌ FAIL'}（门槛 ≥ 90%）\n")

    # 类别分布
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        by_cat.setdefault(r["category"] or "?", []).append(r)
    print("-- 类别通过率 --")
    for cat, rs in sorted(by_cat.items()):
        p = sum(1 for r in rs if r["pass"])
        print(f"  {cat:<12}: {p}/{len(rs)}  ({100*p/len(rs):.0f}%)")

    # 混淆矩阵
    print("\n-- 混淆矩阵（行 = expected, 列 = predicted）--")
    agents = sorted(set(r["expected"] for r in results) | set(r["predicted"] for r in results))
    # 压缩名字到尾缀
    short = {a: a.replace("ascend-", "") if a.startswith("ascend-") else a for a in agents}
    header = "  " + " " * 13 + "".join(f"{short[a]:>12}" for a in agents)
    print(header)
    for row_a in agents:
        cells = []
        for col_a in agents:
            n = sum(1 for r in results if r["expected"] == row_a and r["predicted"] == col_a)
            cells.append(f"{n:>12}")
        print(f"  {short[row_a]:>12}  {''.join(cells)}")

    # 失败题
    fails = [r for r in results if not r["pass"]]
    if fails:
        print(f"\n-- 失败题 {len(fails)} 条 --")
        for r in fails:
            print(f"  ❌ [{r['id']}]  {r['question'][:60]}...")
            print(f"       expected: {r['expected']}")
            print(f"       predicted: {r['predicted']}  (gap={r['confidence_gap']})")
            # 输出 top-3 分数
            top3 = sorted(r["scores"].items(), key=lambda x: -x[1])[:3]
            print(f"       top3: {', '.join(f'{a}={s}' for a,s in top3)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="只跑指定 id")
    ap.add_argument("--category", help="按 category 过滤")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--strict", action="store_true", help="通过率 <90% 时 exit 2")
    ap.add_argument("--file", default="bench/golden-questions.yaml")
    args = ap.parse_args()

    qpath = ROOT / args.file
    if not qpath.exists():
        print(f"[bench] 未找到 {qpath}")
        return 1
    data = parse_yaml_simple(qpath.read_text(encoding="utf-8"))
    results = run(data["questions"], args.id, args.category)

    if args.json:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        print_report(results)

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    rate = 100.0 * passed / total if total else 0.0
    if args.strict and rate < 90:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
