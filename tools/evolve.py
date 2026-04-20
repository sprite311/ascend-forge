#!/usr/bin/env python3
"""
Consolidation 流水线（骨架 stub）。

当前仅打印将要做的事；真正的 merge/dedupe/GC/索引重建需后续填充。
此处故意保持空操作，避免"骨架版"误改用户数据。
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def plan() -> list[str]:
    steps = [
        "1) git status 检查（确保干净）",
        "2) memory/ 查重与合并（按 id + tag + 标题相似度）",
        "3) wiki/ 修 backlink、补 related、标 stale",
        "4) rules/proposals 扫描：证据≥3 且无冲突 → 生成 promote 建议（不直接改 ACTIVE）",
        "5) 重建 memory/INDEX.md、wiki/INDEX.md、wiki/INDEX.jsonl、cases/INDEX.jsonl、skills/INDEX.md",
        "6) 产出 docs/EVOLUTION-STATS.md",
        "7) git add -A && git commit -m 'consolidate: ...'（由用户决定是否执行）",
    ]
    return steps


def main() -> int:
    print(f"[evolve] root = {ROOT}")
    print("[evolve] 骨架阶段——以下动作将来会执行，现仅列出计划：")
    for s in plan():
        print(f"  - {s}")
    print("\n[evolve] 当前为 stub，未执行任何写入。请先在 knowledge-curator 内完成"
          "小规模闭环验证，再逐步把上面 2–6 步迁进本脚本。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
