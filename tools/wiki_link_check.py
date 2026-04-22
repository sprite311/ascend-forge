#!/usr/bin/env python3
"""
Wiki 链接校验 + backlinks 维护 + INDEX.jsonl 生成。

用法：
  python3 tools/wiki_link_check.py            # 干跑：只报告
  python3 tools/wiki_link_check.py --apply    # 写入 INDEX.jsonl + 更新各页 Backlinks
  python3 tools/wiki_link_check.py --strict   # 发现 related 缺失时以 exit 2 失败（CI 用）
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

from _common import ROOT, parse_frontmatter  # noqa: E402

WIKI = ROOT / "wiki"
BACKLINKS_BLOCK_RE = re.compile(
    r"(## Backlinks\s*\n)(.*?)(?=\n## |\Z)", re.DOTALL
)


def collect() -> dict:
    pages: dict = {}
    if not WIKI.exists():
        return pages
    for p in WIKI.rglob("*.md"):
        if p.name.upper() in ("INDEX.MD", "README.MD"):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = parse_frontmatter(text)
        if not fm.get("id"):
            continue
        pages[fm["id"]] = {
            "path": str(p.relative_to(ROOT)),
            "abs": p,
            "fm": fm,
            "text": text,
        }
    return pages


def compute_backlinks(pages: dict) -> dict:
    back: dict = {pid: [] for pid in pages}
    for src, info in pages.items():
        for rid in info["fm"].get("related", []) or []:
            if rid in pages and rid != src:
                back[rid].append(src)
    return {k: sorted(set(v)) for k, v in back.items()}


def write_backlinks(info: dict, backlinks: list[str], pages: dict) -> bool:
    text = info["text"]
    src_path = info["abs"]
    if not backlinks:
        new_block = "<!-- auto -->\n_无反链。_\n"
    else:
        items = []
        for bid in backlinks:
            target = pages[bid]["abs"]
            rel = Path(target).relative_to(src_path.parent.resolve(), walk_up=True) \
                if sys.version_info >= (3, 12) else Path(
                    __import__("os").path.relpath(target, src_path.parent)
                )
            items.append(f"- [{bid}]({rel.as_posix() if hasattr(rel,'as_posix') else rel})")
        new_block = "<!-- auto -->\n" + "\n".join(items) + "\n"

    m = BACKLINKS_BLOCK_RE.search(text)
    if m:
        new = text[:m.start(2)] + new_block + text[m.end():]
        if text.endswith("\n") and not new.endswith("\n"):
            new += "\n"
    else:
        # 无 Backlinks 小节则不强插入；留给 curator 补模板
        return False
    if new != text:
        src_path.write_text(new, encoding="utf-8")
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写入 INDEX.jsonl + 更新 Backlinks")
    ap.add_argument("--strict", action="store_true", help="related 缺失时返回非 0 退出码")
    args = ap.parse_args()

    pages = collect()
    print(f"[wiki-check] 收集到 {len(pages)} 个 wiki 页。")

    missing = []
    for pid, info in pages.items():
        for rid in info["fm"].get("related", []) or []:
            if rid not in pages:
                missing.append((pid, rid))
    if missing:
        print(f"[wiki-check] ⚠️ related 指向不存在的目标 {len(missing)} 条：")
        for a, b in missing[:20]:
            print(f"  - {a} -> {b}")
        if args.strict:
            return 2
    else:
        print("[wiki-check] ✅ 所有 related 指向都存在。")

    # INDEX.jsonl
    out_path = WIKI / "INDEX.jsonl"
    lines = []
    for pid in sorted(pages):
        rec = {"id": pid, **pages[pid]["fm"], "path": pages[pid]["path"]}
        lines.append(json.dumps(rec, ensure_ascii=False))

    if args.apply:
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[wiki-check] ✏️  wrote {out_path} ({len(lines)} lines).")

        # Backlinks
        back = compute_backlinks(pages)
        touched = 0
        for pid, info in pages.items():
            if write_backlinks(info, back[pid], pages):
                touched += 1
        print(f"[wiki-check] ✏️  backlinks 更新了 {touched} 个页面。")
    else:
        print(f"[wiki-check] 预期写入 {out_path} 共 {len(lines)} 行（干跑，未落盘）。")
        print("[wiki-check] 加 --apply 真正写入并同步各页 Backlinks。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
