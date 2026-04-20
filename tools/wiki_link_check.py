#!/usr/bin/env python3
"""
Wiki 链接校验 + backlinks 维护。

功能（骨架）：
- 解析 wiki/**/*.md 的 frontmatter（含 related:）
- 检查 related 指向的 id 是否存在
- 为每个目标页生成 ## Backlinks 清单（幂等更新）
- 输出 wiki/INDEX.jsonl

当前仅做解析 + 干跑报告，不写回文件。
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    # 轻量 yaml 解析：仅支持本项目常用的 key: value / key: [a, b]
    out: dict = {}
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        if ":" not in raw:
            continue
        k, v = raw.split(":", 1)
        k = k.strip()
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            items = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            out[k] = items
        else:
            out[k] = v.strip('"').strip("'")
    return out


def collect() -> dict:
    pages: dict = {}
    if not WIKI.exists():
        return pages
    for p in WIKI.rglob("*.md"):
        if p.name.upper() == "INDEX.MD" or p.name.upper() == "README.MD":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = parse_frontmatter(text)
        if not fm.get("id"):
            continue
        pages[fm["id"]] = {"path": str(p.relative_to(ROOT)), "fm": fm}
    return pages


def main() -> int:
    pages = collect()
    print(f"[wiki-check] 收集到 {len(pages)} 个 wiki 页。")

    # 检查 related 指向
    missing = []
    for pid, info in pages.items():
        for rid in info["fm"].get("related", []) or []:
            if rid not in pages:
                missing.append((pid, rid))
    if missing:
        print(f"[wiki-check] ⚠️ related 指向不存在的目标 {len(missing)} 条：")
        for a, b in missing[:20]:
            print(f"  - {a} -> {b}")
    else:
        print("[wiki-check] ✅ 所有 related 指向都存在。")

    # 导出 INDEX.jsonl
    out_path = WIKI / "INDEX.jsonl"
    lines = []
    for pid in sorted(pages):
        rec = {"id": pid, **pages[pid]["fm"], "path": pages[pid]["path"]}
        lines.append(json.dumps(rec, ensure_ascii=False))
    print(f"[wiki-check] 预期写入 {out_path} 共 {len(lines)} 行（干跑，未落盘）。")

    # 真写：取消下行注释
    # out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
