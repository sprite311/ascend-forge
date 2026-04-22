#!/usr/bin/env python3
"""
Consolidation 流水线（orchestrator）。

按 `.agent/config.yaml.evolution` 执行：
  1) git status 检查（仅报告）
  2) 策略预检 (tools/check_policy.py --from-git)
  3) Wiki 链接校验 + 生成 INDEX.jsonl + 更新 Backlinks (--apply)
  4) Cases 索引重建 (--apply)
  5) Memory TTL 扫描（flag stale）
  6) Wiki draft / TBD 扫描（seed-gap 报告）
  7) Rule proposals 成熟度扫描（evidence 计数，提示 promote）
  8) 输出 docs/EVOLUTION-STATS.md

用法：
  python3 tools/evolve.py            # 预览（部分写入安全，如 INDEX.jsonl）
  python3 tools/evolve.py --apply    # 全量写入
  python3 tools/evolve.py --strict   # 任何警告即 exit != 0（CI）
"""
from __future__ import annotations
import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

# 共享模块（parse_frontmatter / ROOT / banner）见 tools/_common.py
from _common import ROOT, parse_frontmatter as parse_fm, banner  # noqa: E402


def step1_git() -> tuple[int, list[str]]:
    banner("Step 1 · git status")
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    except Exception as e:
        print(f"  ⚠️ git 不可用: {e}")
        return 0, []
    lines = [l for l in out.splitlines() if l.strip()]
    print(f"  工作区 {len(lines)} 条变更。")
    for l in lines[:15]:
        print(f"    {l}")
    if len(lines) > 15:
        print(f"    ... +{len(lines)-15} 条")
    return len(lines), lines


def step2_policy() -> int:
    banner("Step 2 · 策略预检 (check_policy.py)")
    try:
        rc = subprocess.call(
            [sys.executable, str(ROOT / "tools" / "check_policy.py"), "--from-git"],
            cwd=ROOT,
        )
    except Exception as e:
        print(f"  ⚠️ 调用失败: {e}")
        return 1
    return rc


def step3_wiki(apply: bool) -> int:
    banner("Step 3 · Wiki 链接校验 + INDEX.jsonl + Backlinks")
    args = [sys.executable, str(ROOT / "tools" / "wiki_link_check.py")]
    if apply:
        args.append("--apply")
    return subprocess.call(args, cwd=ROOT)


def step4_cases(apply: bool) -> int:
    banner("Step 4 · Cases INDEX.jsonl")
    args = [sys.executable, str(ROOT / "tools" / "rag_index.py")]
    if apply:
        args.append("--apply")
    return subprocess.call(args, cwd=ROOT)


def step5_memory_ttl() -> tuple[int, list[str]]:
    banner("Step 5 · Memory TTL 扫描")
    today = dt.date.today()
    stale = []
    mem = ROOT / "memory"
    for p in mem.rglob("*.md"):
        if p.name.upper() in ("INDEX.MD", "README.MD"):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = parse_fm(text)
        if not fm:
            continue
        try:
            v = fm.get("verified_at", "")
            ttl = int(str(fm.get("ttl_days", "365")))
            if not v:
                continue
            vdate = dt.date.fromisoformat(v)
            age = (today - vdate).days
            if age > ttl:
                stale.append(f"{p.relative_to(ROOT)} (龄 {age}d > ttl {ttl}d)")
        except Exception:
            continue
    if stale:
        print(f"  ⚠️ {len(stale)} 条过期：")
        for s in stale[:20]:
            print(f"    - {s}")
    else:
        print("  ✅ 无过期 memory。")
    return len(stale), stale


def step6_seed_gap() -> tuple[int, list[str]]:
    banner("Step 6 · Wiki draft / TBD 扫描 (seed-gap)")
    gaps = []
    wiki = ROOT / "wiki"
    for p in wiki.rglob("*.md"):
        if p.name.upper() in ("INDEX.MD", "README.MD"):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = parse_fm(text)
        reasons = []
        if fm.get("status") == "draft":
            reasons.append("status=draft")
        tbd_count = len(re.findall(r"\bTBD\b", text))
        if tbd_count:
            reasons.append(f"TBD×{tbd_count}")
        if reasons:
            gaps.append(f"{p.relative_to(ROOT)} · {', '.join(reasons)}")
    if gaps:
        print(f"  ⚠️ {len(gaps)} 个页面有 seed-gap：")
        for g in gaps[:30]:
            print(f"    - {g}")
    else:
        print("  ✅ 无 seed-gap。")
    return len(gaps), gaps


def step6b_wiki_stability() -> int:
    """Step 6b · Wiki draft → stable 升级候选（调 tools/wiki_stability.py --json）。

    子工具 `--json` 输出结构化计数到 stdout，人类报告走 stderr（直接透传给用户）。
    父进程解析 JSON，返回 ready_stable 计数回 ctx['wiki_stable_ready']。
    """
    import json as _json
    banner("Step 6b · Wiki stability（draft → stable 升级候选）")
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "wiki_stability.py"), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as e:
        print(f"  ⚠️ 调 wiki_stability.py 失败：{e}")
        return -1
    # 人类报告（子工具 stderr）透传
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()
    # 解析 JSON 取 ready 计数
    try:
        payload = _json.loads(proc.stdout.strip() or "{}")
        return int(payload.get("tiers", {}).get("ready_stable", 0))
    except Exception as e:
        print(f"  ⚠️ JSON parse 失败：{e}")
        return -1


def step7_proposals() -> tuple[int, list[dict]]:
    banner("Step 7 · Rule proposals 成熟度")
    proposals_dir = ROOT / "rules" / "proposals"
    if not proposals_dir.exists():
        print("  无 proposals 目录。")
        return 0, []
    results = []
    # 用 cases/ 检查 evidence 引用
    cases_texts = []
    for c in (ROOT / "cases").glob("*.md"):
        try:
            cases_texts.append(c.read_text(encoding="utf-8"))
        except Exception:
            pass
    for p in proposals_dir.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        fm = parse_fm(text)
        pid = fm.get("id", p.stem)
        status = fm.get("status", "pending")
        # 计 evidence = fm.evidence 字段 + cases 中对 rule id 的引用
        ev_fm = fm.get("evidence", [])
        if isinstance(ev_fm, str):
            ev_fm = [ev_fm]
        ev_case_refs = sum(1 for t in cases_texts if pid in t)
        total = max(len(ev_fm), ev_case_refs)
        mature = total >= 3
        results.append({
            "id": pid, "status": status, "evidence_count": total,
            "promote_ready": mature, "path": str(p.relative_to(ROOT)),
        })
    # 标记优先级：已 promote > 已 reject/supersede > 🟢 ready > 🟡 pending
    for r in results:
        if r["status"] == "promoted":
            mark = "✅"  # 已晋升，不再计 ready
            r["promote_ready"] = False
        elif r["status"] in ("rejected", "superseded"):
            mark = "⚫"
            r["promote_ready"] = False
        elif r["promote_ready"]:
            mark = "🟢"
        else:
            mark = "🟡"
        print(f"  {mark} {r['id']} · status={r['status']} · evidence={r['evidence_count']} · {r['path']}")
        if r["promote_ready"] and r["status"] == "pending":
            print(f"      → 建议 `python3 tools/promote.py --id {r['id']} --apply`（≥3 证据）")
    return len(results), results


def step8_stats(ctx: dict, apply: bool) -> None:
    banner("Step 8 · EVOLUTION-STATS.md")
    today = dt.date.today().isoformat()
    rules_count = len(list((ROOT / "rules").glob("ACTIVE.md")))
    proposals_count = len(list((ROOT / "rules" / "proposals").glob("*.md"))) if (ROOT / "rules" / "proposals").exists() else 0
    wiki_count = sum(1 for _ in (ROOT / "wiki").rglob("*.md")) - 2  # INDEX + README
    cases_count = sum(1 for _ in (ROOT / "cases").glob("*.md")) - 1
    memory_atoms = sum(1 for _ in (ROOT / "memory").rglob("*.md") if _.name.upper() not in ("INDEX.MD",))

    md = f"""# Evolution Stats

> 由 `tools/evolve.py` 自动生成；不要手改。

- 最后一次 consolidation: `{today}`
- git 变更: {ctx.get('git_changes', 0)}
- Wiki 页: {wiki_count}
- Cases: {cases_count}
- Memory atoms: {memory_atoms}
- Rules (ACTIVE): 载自 `rules/ACTIVE.md`（{rules_count} 文件）
- Rule proposals: {proposals_count}
- Memory TTL 过期: {ctx.get('memory_stale', 0)}
- Wiki seed-gap: {ctx.get('seed_gap', 0)}
- Proposals 成熟（≥3 证据）可 promote: {sum(1 for r in ctx.get('proposals', []) if r['promote_ready'])}

## Seed-gap 清单（status:draft 或含 TBD）
{chr(10).join(f'- {g}' for g in ctx.get('seed_gap_list', [])[:30]) or '_无_'}

## 过期 memory 清单
{chr(10).join(f'- {s}' for s in ctx.get('memory_stale_list', [])[:30]) or '_无_'}

## 待 promote 的 proposal
{chr(10).join(f"- {r['id']} · evidence={r['evidence_count']} · {r['path']}" for r in ctx.get('proposals', []) if r['promote_ready'] and r['status']=='pending') or '_无_'}
"""
    target = ROOT / "docs" / "EVOLUTION-STATS.md"
    if apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(md, encoding="utf-8")
        print(f"  ✏️  wrote {target}")
    else:
        print(f"  (dry) 将写 {target}（{len(md.splitlines())} 行）")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    ctx: dict = {}
    ctx["git_changes"], _ = step1_git()
    _pol = step2_policy()
    step3_wiki(apply=args.apply)
    step4_cases(apply=args.apply)
    ctx["memory_stale"], ctx["memory_stale_list"] = step5_memory_ttl()
    ctx["seed_gap"], ctx["seed_gap_list"] = step6_seed_gap()
    ctx["wiki_stable_ready"] = step6b_wiki_stability()
    _, ctx["proposals"] = step7_proposals()
    step8_stats(ctx, apply=args.apply)

    banner("Summary")
    print(f"  git_changes      : {ctx['git_changes']}")
    print(f"  memory_stale     : {ctx['memory_stale']}")
    print(f"  seed_gap         : {ctx['seed_gap']}")
    print(f"  wiki_stable_ready: {ctx['wiki_stable_ready']}")
    print(f"  proposals_ready  : {sum(1 for r in ctx['proposals'] if r['promote_ready'])}")

    if args.strict and (ctx["memory_stale"] > 0 or ctx["seed_gap"] > 0):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
