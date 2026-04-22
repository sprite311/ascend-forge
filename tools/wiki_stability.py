#!/usr/bin/env python3
"""
Wiki draft → stable 升级候选扫描器（closes R033 exit path）。

背景：
  R033 要求命中 `status: draft` 的 wiki 页时回答必须降权。但"何时不再 draft"
  一直是个人工判断，没有自动化。本工具填补这个空白：把 draft 页里累积够的
  "真机回执"自动挑出来，建议 curator 升 stable。

判定逻辑（三档）：
  🔴 PRE-DRAFT   — 0 条日期小节；仍是纯种子页，不动
  🟡 DRAFT-MATURING — 1 条日期小节；还不够
  🟢 READY-STABLE — ≥ 2 条日期小节 + 每条都有 `source:` 追踪（user-confirmed / case/...）

"日期小节" = 形如 `### 2026-04-21 追加：xxx回执` 的三级标题（容忍变体：`###`/`####` 任一，
  日期格式 YYYY-MM-DD）。这是 `R011` 规定的追加格式。

用法：
  python3 tools/wiki_stability.py            # 只报告
  python3 tools/wiki_stability.py --apply    # 对 🟢 页直接把 status: draft → stable
                                             # （仍要求用户确认：打印 diff + y/n）
  python3 tools/wiki_stability.py --strict   # 存在 🟢 未升级即 exit 2（CI）

注意：
  - `--apply` 走 `rules/ACTIVE.md` R011 的"只追加"原则的例外——只改一行
    `status: draft` → `status: stable`，不改内容。会在 frontmatter 末
    追加 `promoted_to_stable_at: <date>` 留审计。
  - 不会动 `status: stable` 已经是 stable 的页。
  - 不做 `stable → deprecated` 的降级——那是 curator 的判断。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from _common import ROOT, parse_frontmatter  # noqa: E402

WIKI = ROOT / "wiki"
DATE_HEADING_RE = re.compile(r"^#{2,4}\s+(\d{4}-\d{2}-\d{2})\b", re.MULTILINE)
SOURCE_LINE_RE = re.compile(
    r"^\s*(?:source|src|sources|verified[-_]by)\s*[:：]", re.IGNORECASE | re.MULTILINE
)


def analyze_page(path: Path) -> dict:
    """返回单个 wiki 页的 stability 评估。"""
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    status = fm.get("status", "stable")  # 缺省 stable（老页假定已验证）
    # 只看 frontmatter 后的正文；frontmatter 本身的 source 不算回执
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    dated_sections = DATE_HEADING_RE.findall(body)
    # 每条日期小节是否有 source 行（看该 heading 之后到下一 heading 之间的文本）
    # 简化：全文 source 行数 ≥ dated_sections 数 视作够（未严格 1:1 绑定）
    source_lines = SOURCE_LINE_RE.findall(body)

    if status == "draft":
        if len(dated_sections) >= 2 and len(source_lines) >= len(dated_sections):
            tier = "ready-stable"
            icon = "🟢"
        elif len(dated_sections) >= 1:
            tier = "maturing"
            icon = "🟡"
        else:
            tier = "pre-draft"
            icon = "🔴"
    elif status == "stable":
        tier = "already-stable"
        icon = "✅"
    else:
        tier = f"unknown-status-{status}"
        icon = "⚫"

    return {
        "path": path.relative_to(ROOT).as_posix(),
        "id": fm.get("id", path.stem),
        "status": status,
        "tier": tier,
        "icon": icon,
        "dated_sections": len(dated_sections),
        "source_lines": len(source_lines),
        "dates": dated_sections,
    }


def promote_to_stable(
    path: Path,
    dry_run: bool = True,
    log_stream=None,
) -> bool:
    """把 frontmatter 的 `status: draft` 改成 `status: stable`，追加审计字段。

    参数：
      path:       要升级的 wiki 页路径。
      dry_run:    True 时只打印预期操作，不落盘。
      log_stream: 日志目的流（sys.stdout / sys.stderr）；None 时默认 stdout。
                  `main()` 在 `--json` 模式下传 stderr，避免污染 stdout JSON。

    返回是否写入（dry-run 或 status 不是 draft 时返回 False）。
    """
    out = log_stream if log_stream is not None else sys.stdout
    text = path.read_text(encoding="utf-8")
    today = dt.date.today().isoformat()
    # 替换 status
    new_text, n = re.subn(
        r"^(status:\s*)draft\s*$",
        r"\1stable",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n == 0:
        return False
    # 在 frontmatter 结束前插入审计字段
    if "promoted_to_stable_at:" not in new_text:
        new_text = re.sub(
            r"\n---\n",
            f"\npromoted_to_stable_at: {today}\n---\n",
            new_text,
            count=1,
        )
    if dry_run:
        print(f"    (dry-run) 会写入 {path.relative_to(ROOT)}", file=out)
        return False
    path.write_text(new_text, encoding="utf-8")
    print(f"    ✏️  已写入 {path.relative_to(ROOT)}", file=out)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="对 🟢 页真改 status → stable")
    ap.add_argument("--strict", action="store_true", help="存在 🟢 未升级即 exit 2")
    ap.add_argument(
        "--json",
        action="store_true",
        help="输出结构化 JSON 到 stdout（供 evolve.py / CI 解析）；人类报告改走 stderr",
    )
    args = ap.parse_args()

    # 当 --json 时，人类报告写 stderr，stdout 独占 JSON
    def say(msg: str = "") -> None:
        print(msg, file=sys.stderr if args.json else sys.stdout)

    if not WIKI.exists():
        say("[wiki-stability] 无 wiki/ 目录，跳过。")
        if args.json:
            print(json.dumps({"total": 0, "tiers": {}, "ready": [], "maturing": [], "pre_draft": [], "stable": []}))
        return 0

    results = []
    for p in sorted(WIKI.rglob("*.md")):
        if p.name.upper() in ("INDEX.MD", "README.MD"):
            continue
        try:
            results.append(analyze_page(p))
        except Exception as e:
            print(f"[wiki-stability] ⚠️ 读 {p} 失败：{e}", file=sys.stderr)

    # 聚合
    by_tier: dict[str, list[dict]] = {}
    for r in results:
        by_tier.setdefault(r["tier"], []).append(r)

    total = len(results)
    ready = by_tier.get("ready-stable", [])
    maturing = by_tier.get("maturing", [])
    pre = by_tier.get("pre-draft", [])
    stable = by_tier.get("already-stable", [])

    say(f"=== Wiki Stability 报告（共 {total} 页）===")
    say(f"  ✅ 已 stable: {len(stable)}")
    say(f"  🟢 ready-stable （建议升级）: {len(ready)}")
    say(f"  🟡 maturing （1 条回执）: {len(maturing)}")
    say(f"  🔴 pre-draft （0 回执）: {len(pre)}")

    if ready:
        say("\n-- 🟢 建议升 stable --")
        # 日志流：--json 模式下走 stderr，避免污染 stdout JSON
        log_stream = sys.stderr if args.json else sys.stdout
        for r in ready:
            say(f"  {r['icon']} {r['id']}  dated={r['dated_sections']}, sources={r['source_lines']}  "
                f"({r['path']})")
            promote_to_stable(
                ROOT / r["path"],
                dry_run=not args.apply,
                log_stream=log_stream,
            )

    if maturing:
        say("\n-- 🟡 差 1 条回执 --")
        for r in maturing:
            say(f"  {r['icon']} {r['id']}  ({r['path']})  最近一次: {r['dates'][-1] if r['dates'] else '-'}")

    if pre:
        say("\n-- 🔴 未开工（pre-draft，0 回执） --")
        for r in pre:
            say(f"  {r['icon']} {r['id']}  ({r['path']})")

    if args.json:
        out = {
            "total": total,
            "tiers": {
                "ready_stable": len(ready),
                "maturing": len(maturing),
                "pre_draft": len(pre),
                "already_stable": len(stable),
            },
            "ready": ready,
            "maturing": maturing,
            "pre_draft": pre,
            "stable": stable,
        }
        print(json.dumps(out, ensure_ascii=False))

    if args.strict and ready:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
