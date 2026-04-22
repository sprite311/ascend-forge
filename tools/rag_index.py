#!/usr/bin/env python3
"""
给 cases/ 建检索索引。

用法：
  python3 tools/rag_index.py            # 干跑
  python3 tools/rag_index.py --apply    # 写 cases/INDEX.jsonl
  python3 tools/rag_index.py --query "hccl timeout" [--apply]
                                        # 本地 grep-based 检索并打印 top-k

默认后端：grep。想升级到 BM25 请 pip install rank_bm25 并用 --backend=bm25。
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from _common import ROOT, parse_frontmatter  # noqa: E402

CASES = ROOT / "cases"


def collect() -> list[dict]:
    records = []
    if not CASES.exists():
        return records
    for p in sorted(CASES.glob("*.md")):
        if p.name.upper() in ("README.MD",):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = parse_frontmatter(text)
        if not fm.get("id"):
            continue
        records.append({
            "id": fm["id"],
            "path": str(p.relative_to(ROOT)),
            "tags": fm.get("tags", []),
            "models": fm.get("models", []),
            "hardware": fm.get("hardware", []),
            "software": fm.get("software", []),
            "outcome": fm.get("outcome", ""),
            "date": fm.get("date", ""),
            "_text": text,
        })
    return records


def grep_score(query: str, rec: dict) -> int:
    q = query.lower()
    score = 0
    score += rec["_text"].lower().count(q) * 1
    score += sum(1 for t in rec.get("tags", []) if q in str(t).lower()) * 5
    if q in rec["id"].lower():
        score += 10
    return score


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写 cases/INDEX.jsonl")
    ap.add_argument("--query", help="检索关键词；打印 top-k 匹配")
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()

    records = collect()
    print(f"[rag-index] 收集 {len(records)} case。")

    if args.query:
        scored = [(grep_score(args.query, r), r) for r in records]
        scored.sort(key=lambda x: -x[0])
        print(f"[rag-index] 检索 '{args.query}' top-{args.top_k}：")
        for s, r in scored[:args.top_k]:
            if s == 0:
                continue
            print(f"  - [{s:>4}] {r['id']} · {r['path']} · tags={r['tags']}")

    out = CASES / "INDEX.jsonl"
    if args.apply:
        # strip _text before serializing
        clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in records]
        out.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in clean) + ("\n" if clean else ""),
            encoding="utf-8",
        )
        print(f"[rag-index] ✏️  wrote {out} ({len(clean)} lines).")
    else:
        print(f"[rag-index] 将写入 {out}（干跑，加 --apply 真正写入）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
