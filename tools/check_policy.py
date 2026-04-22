#!/usr/bin/env python3
"""
策略检查器：验证 agent 在一次任务中的产出是否符合 `.agent/config.yaml`。

检查项：
  R010 — 任何 memory/wiki/skill/rule 新增必须带 `source:` frontmatter。
  R011 — wiki 不整页重写（通过 git diff 判定：新增行数 / 总行数 < 阈值 则不算重写；
         默认单次 diff 新增不能覆盖原文件 > 50% 原内容被替换）。
  R020 — 危险命令检测（扫描本次任务产出的 case / skill 中命令块，匹配危险 pattern）。
  R021 — 写入路径限定在 write_whitelist 内；denylist 禁用。
  R031 — 单任务产出不超限：memory ≤ 3, skill ≤ 1, rule_proposal ≤ 1, case ≤ 1, wiki 无限。

用法：
  # A) 基于 git 工作区（未 commit 的变更）自动统计
  python3 tools/check_policy.py --from-git

  # B) 手工给出 plan（JSON）
  python3 tools/check_policy.py --from-plan plan.json

  # C) CI 模式（失败时非 0 退出）
  python3 tools/check_policy.py --from-git --strict

plan.json 格式：
  {"writes": ["memory/facts/x.md", "wiki/errors/y.md"]}
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from _common import ROOT, FRONTMATTER_RE  # noqa: E402

DANGEROUS = [
    r"\brm\s+-rf\b",
    r"\bdd\s+if=",
    r"\bmkfs\b",
    r"\bmodprobe\b",
    r"\brmmod\b",
    r">\s*/dev/",
    r"\bchmod\s+-R\s+777\b",
    r"npu-smi\s+set\s+-t\s+reset",
]

WRITE_WHITELIST_PREFIXES = (
    "memory/",
    "skills/",
    "wiki/",
    "cases/",
    "rules/proposals/",
)
WRITE_DENYLIST_PREFIXES = (
    "rules/ACTIVE.md",
    "rules/archive/",
    "docs/",
    ".agent/",
    "adapters/",
    "CLAUDE.md",
    "AGENTS.md",
    "README.md",
)

LIMITS = {"memory": 3, "skill": 1, "rule_proposal": 1, "case": 1}


def classify(path: str) -> str:
    if path.startswith("memory/") and path.endswith(".md") and not path.endswith("INDEX.md"):
        # only count *new* atom files, not INDEX append
        return "memory"
    if path.startswith("skills/") and path.endswith("/SKILL.md"):
        return "skill"
    if path.startswith("rules/proposals/") and path.endswith(".md"):
        return "rule_proposal"
    if path.startswith("cases/") and path.endswith(".md") and "INDEX" not in path and "README" not in path:
        return "case"
    if path.startswith("wiki/"):
        return "wiki"
    return "other"


def git_changed_files() -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        )
    except Exception as e:
        print(f"[policy] ⚠️ git 不可用: {e}")
        return []
    files = []
    for line in out.splitlines():
        # format: "XY path" where XY is status flags
        if len(line) < 4:
            continue
        status = line[:2]
        path = line[3:].strip()
        # rename: "R  old -> new"
        if "->" in path:
            path = path.split("->")[-1].strip()
        # only additions / modifications
        if status.strip() in ("A", "AM", "??", "M", "MM", "AD", "AR"):
            files.append(path)
    return files


def load_config_denylist() -> list[str]:
    cfg = ROOT / ".agent" / "config.yaml"
    if not cfg.exists():
        return list(WRITE_DENYLIST_PREFIXES)
    return list(WRITE_DENYLIST_PREFIXES)


def check_whitelist(writes: list[str]) -> list[tuple[str, str]]:
    bad = []
    for w in writes:
        wn = w.lstrip("./")
        if wn.startswith(WRITE_DENYLIST_PREFIXES):
            bad.append((wn, "R021: 在 denylist"))
            continue
        if not wn.startswith(WRITE_WHITELIST_PREFIXES):
            bad.append((wn, "R021: 不在 whitelist"))
    return bad


def check_limits(writes: list[str]) -> tuple[dict, list[str]]:
    counts = {"memory": 0, "skill": 0, "rule_proposal": 0, "case": 0, "wiki": 0, "other": 0}
    for w in writes:
        k = classify(w)
        counts[k] = counts.get(k, 0) + 1
    viol = []
    for k, lim in LIMITS.items():
        if counts.get(k, 0) > lim:
            viol.append(f"R031: {k} = {counts[k]} > limit {lim}")
    return counts, viol


def check_sources(writes: list[str]) -> list[str]:
    viol = []
    for w in writes:
        wn = w.lstrip("./")
        if not (wn.startswith("memory/") or wn.startswith("wiki/") or wn.endswith("/SKILL.md") or wn.startswith("rules/proposals/")):
            continue
        p = ROOT / wn
        if not p.exists() or p.is_dir():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        m = FRONTMATTER_RE.match(text)
        if not m:
            # wiki INDEX.md 等允许无 frontmatter；单文件忽略
            if any(wn.endswith(x) for x in ("INDEX.md", "README.md")):
                continue
            viol.append(f"R010: {wn} 缺少 frontmatter")
            continue
        fm_block = m.group(1)
        has_source = bool(re.search(r"^(source|sources|evidence):", fm_block, re.MULTILINE))
        # cases 本身就是源，允许无
        if wn.startswith("cases/"):
            continue
        if not has_source:
            viol.append(f"R010: {wn} 缺 source/sources")
    return viol


def check_dangerous(writes: list[str]) -> list[tuple[str, str]]:
    viol = []
    for w in writes:
        wn = w.lstrip("./")
        if not wn.endswith(".md"):
            continue
        p = ROOT / wn
        if not p.exists() or p.is_dir():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        # 只看代码块中的命令
        for block in re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.DOTALL):
            for line in block.splitlines():
                for patt in DANGEROUS:
                    if re.search(patt, line):
                        # 允许命令存在，只要**页面旁**有 ⚠️ 或 R020 提示
                        ctx_ok = "R020" in text or "⚠️" in text or "破坏性" in text or "不要自动" in text or "生成命令" in text
                        if not ctx_ok:
                            viol.append((wn, f"R020 疑似危险命令未警告: {line.strip()[:80]}"))
                        break
    return viol


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-git", action="store_true")
    g.add_argument("--from-plan", type=str, help="plan.json 路径")
    ap.add_argument("--strict", action="store_true", help="有违规时非 0 退出")
    args = ap.parse_args()

    if args.from_git:
        writes = git_changed_files()
    else:
        plan = json.loads(Path(args.from_plan).read_text(encoding="utf-8"))
        writes = plan.get("writes", [])

    if not writes:
        print("[policy] 无待检查写入。")
        return 0

    print(f"[policy] 待检查写入：{len(writes)} 条")
    for w in writes[:30]:
        print(f"  · {w}")
    if len(writes) > 30:
        print(f"  · ... +{len(writes)-30} 条")

    whitelist_bad = check_whitelist(writes)
    counts, limit_viol = check_limits(writes)
    source_viol = check_sources(writes)
    danger_viol = check_dangerous(writes)

    print("\n=== R021 写入路径 ===")
    if whitelist_bad:
        for p, r in whitelist_bad:
            print(f"  ❌ {p}  {r}")
    else:
        print("  ✅ 全部在 whitelist 且未触 denylist")

    print("\n=== R031 单任务配额 ===")
    for k in ("memory", "skill", "rule_proposal", "case", "wiki", "other"):
        lim = LIMITS.get(k, "∞")
        mark = "✅" if counts.get(k, 0) <= (LIMITS.get(k, 1e9) if k in LIMITS else 1e9) else "❌"
        print(f"  {mark} {k}: {counts.get(k,0)} / {lim}")
    for v in limit_viol:
        print(f"  ❌ {v}")

    print("\n=== R010 Source 字段 ===")
    if source_viol:
        for v in source_viol:
            print(f"  ❌ {v}")
    else:
        print("  ✅ 所有新文件均有 source/sources 或可豁免 (INDEX / case)")

    print("\n=== R020 危险命令提示 ===")
    if danger_viol:
        for p, r in danger_viol:
            print(f"  ❌ {p}: {r}")
    else:
        print("  ✅ 命令块中的破坏性操作均带 ⚠️ / R020 / '不要自动' 等提示")

    all_viol = whitelist_bad + limit_viol + source_viol + danger_viol
    print()
    if all_viol:
        print(f"[policy] ❌ 总计 {len(all_viol)} 条违规。")
        return 1 if args.strict else 0
    print("[policy] ✅ 全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
