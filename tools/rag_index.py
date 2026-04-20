#!/usr/bin/env python3
"""
给 cases/ 建检索索引（骨架 stub）。

默认后端：grep / BM25（rank_bm25）。如启用 embedding，可后续加 sentence-transformers 分支。

当前仅从 cases/*.md 读 frontmatter，写 cases/INDEX.jsonl。不做向量化。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "cases"


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    body = text[3:end]
    out: dict = {}
    for raw in body.splitlines():
        if not raw.strip() or raw.startswith("#") or ":" not in raw:
            continue
        k, v = raw.split(":", 1)
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            out[k] = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
        else:
            out[k] = v.strip('"').strip("'")
    return out


def main() -> int:
    if not CASES.exists():
        print(f"[rag-index] {CASES} 不存在。")
        return 0
    records = []
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
        rec = {
            "id": fm["id"],
            "path": str(p.relative_to(ROOT)),
            "tags": fm.get("tags", []),
            "models": fm.get("models", []),
            "hardware": fm.get("hardware", []),
            "software": fm.get("software", []),
            "outcome": fm.get("outcome", ""),
            "date": fm.get("date", ""),
        }
        records.append(rec)
    out = CASES / "INDEX.jsonl"
    print(f"[rag-index] 收集 {len(records)} case；将写入 {out}（干跑）。")
    # 真写：取消下行注释
    # out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + ("\n" if records else ""), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
