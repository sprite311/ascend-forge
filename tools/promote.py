#!/usr/bin/env python3
"""
Rule proposal → ACTIVE.md 提升器。

背景：`tools/evolve.py` Step 7 会在 evidence ≥ 3 时把 proposal 标为 🟢 promote_ready。
本脚本负责执行实际 promote：把 proposal 内容 append 到 `rules/ACTIVE.md`、
把原 proposal 归档到 `rules/archive/promoted-<date>-<id>.md`。

设计：
  - 默认 --dry-run：打印将发生的 3 个动作，不落盘。
  - --apply 才真写。
  - --id <proposal-id> 指定某条；不给就 promote 所有 🟢 ready 的。
  - 生成 rule 编号：扫 ACTIVE.md 现有 Rxxx，取最大值 +1（保留分组 R0xx/R1xx/R2xx/R3xx）。
  - 分组：按 proposal frontmatter `applies_to` 字段粗分（knowledge/safety/evolution/planning）。

用法：
  python3 tools/promote.py                                    # 列出所有 🟢，dry-run
  python3 tools/promote.py --id seed-critical-wiki-before-first-use --dry-run
  python3 tools/promote.py --id seed-critical-wiki-before-first-use --apply

注意：
  promote 后，原 proposal 文件消失（移动到 archive），evolve.py 下一次跑
  step 7 就不再显示该条。请在 commit message 里说明"promoted R0XX"。
"""
from __future__ import annotations
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from _common import ROOT, parse_frontmatter as parse_fm, strip_frontmatter  # noqa: E402

PROPOSALS = ROOT / "rules" / "proposals"
ACTIVE = ROOT / "rules" / "ACTIVE.md"
ARCHIVE = ROOT / "rules" / "archive"

RULE_ID_RE = re.compile(r"\*\*R(\d{3})\*\*")


def collect_evidence(pid: str) -> int:
    """与 evolve.py Step 7 同款计数：fm evidence + cases/*.md 中的 pid 字符串引用。"""
    p = PROPOSALS / f"2026-04-20-{pid}.md"
    # 兼容前缀不是 2026-04-20 的 proposal：glob fallback
    if not p.exists():
        candidates = list(PROPOSALS.glob(f"*{pid}*.md"))
        if candidates:
            p = candidates[0]
    if not p.exists():
        return 0
    fm = parse_fm(p.read_text(encoding="utf-8"))
    ev_fm = fm.get("evidence", [])
    if isinstance(ev_fm, str):
        ev_fm = [ev_fm]
    case_refs = 0
    for c in (ROOT / "cases").glob("*.md"):
        try:
            if pid in c.read_text(encoding="utf-8"):
                case_refs += 1
        except Exception:
            pass
    return max(len(ev_fm), case_refs)


def find_ready_proposals() -> list[tuple[str, Path]]:
    """扫 proposals/，返回 evidence ≥ 3 且 status=pending 的条目。"""
    ready = []
    if not PROPOSALS.exists():
        return ready
    for p in sorted(PROPOSALS.glob("*.md")):
        fm = parse_fm(p.read_text(encoding="utf-8"))
        pid = fm.get("id", p.stem)
        status = fm.get("status", "pending")
        if status != "pending":
            continue
        ev = collect_evidence(pid)
        if ev >= 3:
            ready.append((pid, p))
    return ready


def next_rule_id(section: str) -> str:
    """扫 ACTIVE.md 现有 Rxxx，按 section 分组返回下一个可用编号。

    编号段：
      R0xx — Planning
      R1xx — Knowledge hygiene
      R2xx — Safety
      R3xx — Evolution
    """
    text = ACTIVE.read_text(encoding="utf-8") if ACTIVE.exists() else ""
    used = [int(m.group(1)) for m in RULE_ID_RE.finditer(text)]
    section_base = {
        "planning": 0,
        "knowledge": 10,
        "safety": 20,
        "evolution": 30,
    }.get(section, 30)  # default to evolution
    candidates = [n for n in used if section_base <= n < section_base + 10]
    if not candidates:
        return f"R{section_base:03d}"
    return f"R{max(candidates) + 1:03d}"


def classify_section(fm: dict) -> str:
    """按 applies_to / tags / id 粗分组。"""
    blob = " ".join(fm.get("applies_to", []) + fm.get("tags", []) + [fm.get("id", "")]).lower()
    if any(k in blob for k in ("safety", "危险", "破坏")):
        return "safety"
    if any(k in blob for k in ("curator", "consolidation", "evolve", "promote")):
        return "evolution"
    if any(k in blob for k in ("wiki", "memory", "knowledge", "source", "seed")):
        return "knowledge"
    return "evolution"


def build_active_entry(rule_id: str, pid: str, fm: dict, body: str, evidence: int) -> str:
    """把 proposal 正文压缩成 ACTIVE.md 单条（1-2 行 + evidence 脚注）。"""
    today = dt.date.today().isoformat()
    # 取 body 里第一个以 "## 规则" 之后的第一段作为摘要
    m = re.search(r"##\s*规则\s*\n(.+?)(?=\n##|\Z)", body, re.DOTALL)
    summary_raw = m.group(1).strip() if m else body.strip().split("\n\n")[0]
    # 压成 ≤ 2 行
    first_sent = re.split(r"(?<=[。！!\.])\s+|\n\n", summary_raw.strip())[0]
    summary = re.sub(r"\s+", " ", first_sent).strip()
    if len(summary) > 220:
        summary = summary[:215] + "…"
    return (
        f"\n- **{rule_id}** {summary}\n"
        f"  *evidence: {evidence} cases · promoted from `{pid}` · since {today}*\n"
    )


def run_promotion(pid: str, proposal_path: Path, apply: bool) -> None:
    text = proposal_path.read_text(encoding="utf-8")
    fm = parse_fm(text)
    body = strip_frontmatter(text)
    evidence = collect_evidence(pid)
    section = classify_section(fm)
    rule_id = next_rule_id(section)
    entry = build_active_entry(rule_id, pid, fm, body, evidence)
    today = dt.date.today().isoformat()
    archive_path = ARCHIVE / f"promoted-{today}-{pid}.md"

    print(f"\n=== Promote {pid} → {rule_id}（section: {section}）===")
    print(f"  evidence: {evidence} (threshold ≥ 3)")
    print(f"  ACTIVE.md append 预览：")
    for line in entry.splitlines():
        print(f"    {line}")
    print(f"  archive 目标: {archive_path.relative_to(ROOT)}")

    if not apply:
        print(f"  (dry-run) 加 --apply 真落盘。")
        return

    # 1) append to ACTIVE.md（找对应 section，把条目插到 section 末尾；若没找到则 append 到文件末）
    active_text = ACTIVE.read_text(encoding="utf-8")
    section_name = {"safety": "## Safety", "evolution": "## Evolution",
                    "knowledge": "## Knowledge hygiene", "planning": "## Planning"}[section]
    # 插入点：本 section 末尾 = 下一个 `## ` 或 `---` 分隔线 或 文件末
    # （之前的 bug：没检测 `---`，结果规则被插到了尾部的 `---`/`## 说明` 之间，视觉上"游离"）
    sec_match = re.search(re.escape(section_name) + r"\s*\n", active_text)
    if sec_match:
        start = sec_match.end()
        # 同时匹配 `\n## ` 和 `\n---\n` 作为 section 终止符
        nxt = re.search(r"\n(##\s|---\s*\n)", active_text[start:])
        end = start + nxt.start() if nxt else len(active_text)
        # 去掉 end 位置前多余空行
        while end > 0 and active_text[end - 1] == "\n":
            end -= 1
        new_active = active_text[:end] + entry + active_text[end:]
    else:
        # 追加新 section（插到第一个 `---` 分隔符前；无则 append）
        divider = re.search(r"\n---\s*\n", active_text)
        if divider:
            pos = divider.start()
            new_active = active_text[:pos].rstrip() + f"\n\n{section_name}\n{entry}\n" + active_text[pos:]
        else:
            new_active = active_text.rstrip() + f"\n\n{section_name}\n{entry}\n"
    ACTIVE.write_text(new_active, encoding="utf-8")
    print(f"  ✏️  ACTIVE.md 已更新（+{len(entry.splitlines())} 行）")

    # 2) archive 原 proposal
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archive_text = (
        f"<!-- Promoted {today} to ACTIVE as {rule_id}. Original proposal below. -->\n\n"
        + text
    )
    archive_path.write_text(archive_text, encoding="utf-8")
    print(f"  ✏️  archive 已写 {archive_path.relative_to(ROOT)}")

    # 3) remove original proposal (若沙箱不允许 unlink，fallback 到标记 status: promoted)
    try:
        proposal_path.unlink()
        print(f"  🗑  原 proposal 已删（{proposal_path.relative_to(ROOT)}）")
    except (PermissionError, OSError) as e:
        # 把 status 改成 promoted + 追 promoted_to / promoted_at / archive_ref 字段
        old = proposal_path.read_text(encoding="utf-8")
        new = re.sub(
            r"^(status:\s*)pending.*$",
            f"\\1promoted",
            old,
            count=1,
            flags=re.MULTILINE,
        )
        if "promoted_at:" not in new:
            # 在 frontmatter 结束前插入
            new = re.sub(
                r"\n---\n",
                f"\npromoted_at: {today}\npromoted_to: {rule_id}\narchive_ref: {archive_path.relative_to(ROOT).as_posix()}\n---\n",
                new,
                count=1,
            )
        proposal_path.write_text(new, encoding="utf-8")
        print(f"  ⚠️  unlink 失败（{e}）；fallback：status → promoted（文件保留）")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="proposal id；不给则列出所有 ready")
    ap.add_argument("--apply", action="store_true", help="真落盘（默认 dry-run）")
    args = ap.parse_args()

    ready = find_ready_proposals()
    if not ready:
        print("[promote] 无 evidence ≥ 3 的 pending proposal。")
        return 0

    print(f"[promote] 发现 {len(ready)} 条 🟢 promote_ready:")
    for pid, p in ready:
        print(f"  · {pid}  ({p.relative_to(ROOT)})")

    if args.id:
        targets = [(pid, p) for pid, p in ready if pid == args.id]
        if not targets:
            print(f"\n[promote] id={args.id} 不在 ready 列表。")
            return 1
    else:
        targets = ready
        if args.apply:
            print("\n[promote] --apply 但未指定 --id；为安全起见一次只 promote 一条，请加 --id。")
            return 1

    for pid, p in targets:
        run_promotion(pid, p, apply=args.apply)

    return 0


if __name__ == "__main__":
    sys.exit(main())
