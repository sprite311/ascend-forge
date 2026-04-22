#!/usr/bin/env python3
"""
skill_audit.py — 盘点 `skills/` 下每个 skill 的"从 SOP 到可执行"的差距。

产出背景：
  Wave 8 close 里我基于 compaction summary 断言 "skills: 0"，实际 `ls` 发现
  有 12 个。为防下次再用"记忆"而不是"事实"做架构判断，本工具强制所有关于
  skill 层的定量陈述都**可以被跑出来**，而不是回想出来。
  配对 `memory/pitfalls/pitfall-cross-session-state-amnesia.md`。

评分维度（每份 SKILL.md）：
  - has_sop       — 有 SOP 段（## 步骤 / ## 5 步 / ## SOP 等）
  - has_run       — 目录下有 run.sh / run.py / *.sh / scripts/ 下可执行文件
  - has_tool_ref  — SOP 文本里出现 `tools/<name>.py` 引用（说明有工具背书）
  - has_source    — frontmatter 或 "版本历史" 段里引用 `case/` 或 `user-confirmed`
  - owners        — frontmatter.owners 列表
  - triggers      — frontmatter.trigger 列表长度
  - lines         — 文件行数
  - last_modified — 最近修改日期（git 里是不是近三个月有改）

不做的事：
  - 不做 skill 质量评分（太主观）
  - 不按 owner 聚合（交给 evolve.py Step X 未来做）
  - 不写 skill 文件（只读）

用法：
  python3 tools/skill_audit.py              # 表格（stdout）
  python3 tools/skill_audit.py --json       # 机器可读 JSON
  python3 tools/skill_audit.py --gap        # 只打"需要补" 的 skill（has_sop 但 !has_run）
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from _common import ROOT, parse_frontmatter  # noqa: E402

SKILLS = ROOT / "skills"
SOP_HEADING_RE = re.compile(r"^#{2,3}\s*(步骤|SOP|[0-9]+\s*步|Steps?|Playbook)", re.MULTILINE | re.IGNORECASE)
TOOL_REF_RE = re.compile(r"tools/([a-z_][\w]*)\.py", re.IGNORECASE)
SOURCE_REF_RE = re.compile(r"\b(case/|user[- ]confirmed|source\s*[:：])", re.IGNORECASE)


def audit_one(skill_dir: Path) -> dict:
    """读一个 skills/<name>/ 目录，返回 audit 结果字典。"""
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"name": name, "error": "no SKILL.md", "skipped": True}

    text = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)

    # has_run: 目录里是否有 run.sh / run.py / scripts/ 下 *.sh
    has_run = False
    run_files: list[str] = []
    for candidate in ["run.sh", "run.py", "Makefile"]:
        if (skill_dir / candidate).exists():
            has_run = True
            run_files.append(candidate)
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        execs = [p.name for p in scripts_dir.iterdir() if p.is_file()]
        if execs:
            has_run = True
            run_files.extend(f"scripts/{e}" for e in execs)

    # has_sop: 正文里有 SOP / 步骤 / N 步 heading
    has_sop = bool(SOP_HEADING_RE.search(text))

    # has_tool_ref: 引用 tools/*.py
    tool_refs = sorted(set(TOOL_REF_RE.findall(text)))

    # has_source: frontmatter.source 或正文提及
    has_source = bool(fm.get("source")) or bool(SOURCE_REF_RE.search(text))

    # owners / triggers
    owners = fm.get("owners", [])
    if isinstance(owners, str):
        owners = [owners]
    triggers = fm.get("trigger", [])
    if isinstance(triggers, str):
        triggers = [triggers]

    return {
        "name": name,
        "path": str(skill_md.relative_to(ROOT)),
        "lines": text.count("\n") + 1,
        "has_sop": has_sop,
        "has_run": has_run,
        "run_files": run_files,
        "has_tool_ref": bool(tool_refs),
        "tool_refs": tool_refs,
        "has_source": has_source,
        "owners": owners,
        "triggers_count": len(triggers),
        "version": fm.get("version", ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gap", action="store_true",
                    help="只列 has_sop=True 但 has_run=False 的 skill（最该补 runfile 的）")
    args = ap.parse_args()

    if not SKILLS.is_dir():
        print("skills/ 不存在", file=sys.stderr)
        return 1

    rows = []
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir():
            continue
        if d.name.startswith("."):
            continue
        rows.append(audit_one(d))

    # 聚合信号
    total = len(rows)
    with_sop = sum(1 for r in rows if r.get("has_sop"))
    with_run = sum(1 for r in rows if r.get("has_run"))
    with_tool = sum(1 for r in rows if r.get("has_tool_ref"))
    with_src = sum(1 for r in rows if r.get("has_source"))
    gap_rows = [r for r in rows if r.get("has_sop") and not r.get("has_run")]

    if args.json:
        out = {
            "date": dt.date.today().isoformat(),
            "totals": {
                "total": total,
                "has_sop": with_sop,
                "has_run": with_run,
                "has_tool_ref": with_tool,
                "has_source": with_src,
                "doc_to_auto_gap": len(gap_rows),
            },
            "skills": rows,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"=== Skill Audit · {total} skills ===\n")
    if args.gap:
        print(f"GAP · has SOP but no runfile（{len(gap_rows)}/{total}）:\n")
        for r in gap_rows:
            tools = "+".join(r["tool_refs"]) if r["tool_refs"] else "(no tool refs)"
            print(f"  • {r['name']:<38} owners={r['owners']}  tools={tools}")
        return 0

    header = f"{'name':<38} {'SOP':<4} {'run':<4} {'tool':<5} {'src':<4} {'lines':<6} owners"
    print(header)
    print("-" * len(header))
    for r in rows:
        flags = lambda b: "✅" if b else "—"  # noqa
        tools = ",".join(r["tool_refs"]) if r["tool_refs"] else "-"
        owners = "/".join(r["owners"]) if r["owners"] else "-"
        print(
            f"{r['name']:<38} {flags(r['has_sop']):<4} {flags(r['has_run']):<4} "
            f"{flags(r['has_tool_ref']):<5} {flags(r['has_source']):<4} "
            f"{r['lines']:<6} {owners}"
        )

    print()
    print(f"有 SOP     : {with_sop}/{total}")
    print(f"有 runfile : {with_run}/{total}  ← 目标是全部 ✅")
    print(f"引工具     : {with_tool}/{total}")
    print(f"有 source  : {with_src}/{total}")
    print(f"⚠ 缺口     : {len(gap_rows)} 个 skill 有 SOP 但无 runfile（跑 --gap 看清单）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
