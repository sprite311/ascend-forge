#!/usr/bin/env python3
"""
Curator 候选抽取器（heuristic-only，非 LLM）。

用途：`@knowledge-curator` 的 EXTRACT 步骤（第 3 步）从 prose 升级成可执行脚本。
把一份会话 trace（纯文本或 markdown）喂进来，按启发式规则扫出**候选知识**，
输出 JSON 结构供 curator agent 决定哪条落盘。

设计原则：
  - **纯启发式**：只用正则和关键词匹配，不调任何 LLM。
  - **保守**：宁可漏一条也不乱写；置信度不够就 `confidence: low` 并提示 curator 复核。
  - **去重**：扫 `memory/INDEX.md` + `wiki/INDEX.jsonl` 找现有实体，标记 `dedupe_hit`。
  - **只读**：本脚本**从不写任何 memory/wiki/rule**——输出纯报告给 curator/用户。

启发式类别：
  fact        — 带数字/版本号的事实断言（"CANN 8.0.RC2"、"显存 64GB"）
  lesson      — "发现/教训/now I know/其实"
  pitfall     — "坑/踩了/没想到/wrong/失败"
  preference  — 用户第一人称："记住/以后都/我偏好/always use/不要再/don't"
  rule        — 普适命令句："必须/禁止/always/never/forbid/must"
  wiki-append — trace 提到的 wiki id / alias 命中
  case        — 整个 trace 本身（1 条）

输出示例（截断）：
  {
    "case_candidate": {"slug": "...", "date": "...", "title": "..."},
    "candidates": [
      {"kind": "pitfall", "summary": "...", "evidence": "...", "confidence": "medium", "dedupe_hit": null},
      ...
    ],
    "counts_by_kind": {...},
    "r031_advice": {"memory_to_land": [...], "skill_to_land": [...], ...}
  }

用法：
  cat trace.md | python3 tools/curate.py
  python3 tools/curate.py --trace trace.md
  python3 tools/curate.py --trace trace.md --slug qwen3-oom --json | jq .
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ─── 启发式 pattern ────────────────────────────────────────────────────────────

KIND_PATTERNS: dict[str, list[str]] = {
    "pitfall": [
        r"坑",
        r"踩了",
        r"没想到",
        r"结果.*(失败|错|崩)",
        r"\bfailed\b",
        r"\bwrong\b",
        r"原来.*不是",
        r"竟然",
    ],
    "lesson": [
        r"教训",
        r"发现.*其实",
        r"now I know",
        r"学到",
        r"经验.*[:：]",
    ],
    "preference": [
        r"记住",
        r"以后都",
        r"以后(别|不要)",
        r"我偏好",
        r"我一般",
        r"\balways use\b",
        r"\bdon't\b.*(?:again|anymore)",
    ],
    "rule": [
        r"必须",
        r"禁止",
        r"\balways\b",
        r"\bnever\b",
        r"\bforbid\b",
        r"\bmust\b",
        r"应当",
        r"不得",
    ],
    "fact": [
        r"\bCANN\s+\d+\.\d+",
        r"\btorch\s*==?\s*\d+\.\d+",
        r"\btorch_npu\s*==?\s*\d+\.\d+",
        r"显存\s*\d+\s*GB",
        r"\bHBM\s*\d+",
        r"\d+\s*TOPS",
        r"\bAtlas\s+\d{3,4}",
        r"\b910[BC]\b",
        r"\b310[PB]\b",
    ],
}


# ─── 去重：查现有 memory / wiki 索引 ────────────────────────────────────────────

def load_memory_ids() -> set[str]:
    idx = ROOT / "memory" / "INDEX.md"
    if not idx.exists():
        return set()
    ids = set()
    # format: [id](kind/id.md) — ...
    for m in re.finditer(r"\[([a-z0-9\-]+)\]\(", idx.read_text(encoding="utf-8")):
        ids.add(m.group(1))
    return ids


def load_wiki_entities() -> dict[str, dict]:
    """返回 {id: {title, aliases, tags, kind}} 方便精确/别名匹配"""
    idx = ROOT / "wiki" / "INDEX.jsonl"
    out: dict = {}
    if not idx.exists():
        return out
    for line in idx.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        out[rec["id"]] = rec
    return out


# ─── 候选抽取 ─────────────────────────────────────────────────────────────────

def sentence_iter(text: str):
    """粗粒度分句：按中英文句号 / 换行切。"""
    for chunk in re.split(r"(?<=[。！？!?\.])\s+|\n{2,}", text):
        s = chunk.strip()
        if s:
            yield s


def scan_kinds(text: str) -> list[dict]:
    """按 KIND_PATTERNS 扫文本，返回候选列表。每个候选带 kind / evidence / confidence。"""
    found: list[dict] = []
    for sent in sentence_iter(text):
        matched_kinds: list[str] = []
        for kind, patts in KIND_PATTERNS.items():
            for patt in patts:
                if re.search(patt, sent, re.IGNORECASE):
                    matched_kinds.append(kind)
                    break
        for kind in matched_kinds:
            conf = "medium"
            # 用户第一人称表达的 preference/rule → high
            if kind in ("preference", "rule") and re.search(r"^(我|you|please|用户)", sent, re.IGNORECASE):
                conf = "high"
            # 纯 fact 数字断言但无出处 → low（因为可能是臆断）
            if kind == "fact" and not re.search(r"(参[照考].*|source:|根据|来自|官方|文档)", sent):
                conf = "low"
            found.append({
                "kind": kind,
                "summary": sent[:140] + ("…" if len(sent) > 140 else ""),
                "evidence": sent[:400],
                "confidence": conf,
            })
    return found


def detect_wiki_mentions(text: str, entities: dict[str, dict]) -> list[dict]:
    """看 trace 里是否直接点到了现有 wiki 实体的 id / alias / title。"""
    hits: list[dict] = []
    for pid, rec in entities.items():
        names = {pid, rec.get("title", "")} | set(rec.get("aliases", []) or [])
        for n in names:
            if not n:
                continue
            if re.search(r"\b" + re.escape(n) + r"\b", text, re.IGNORECASE):
                hits.append({
                    "kind": "wiki-append",
                    "target_id": pid,
                    "target_path": rec.get("path", ""),
                    "matched_name": n,
                    "summary": f"trace 提到 wiki 实体 `{pid}`（命中 `{n}`）；考虑 append 新段落",
                    "confidence": "medium",
                })
                break  # 一页只算一次
    return hits


def dedupe_memory(candidates: list[dict], existing_ids: set[str]) -> list[dict]:
    """给 memory-kind 候选打 dedupe_hit：看 summary 里是否包含已有 id 的关键词。"""
    out = []
    for c in candidates:
        hit = None
        summary = c.get("summary", "")
        for mid in existing_ids:
            # e.g. pitfall-block-size-alignment → "block size" / "block-size"
            tokens = [t for t in mid.split("-") if len(t) > 3]
            if not tokens:
                continue
            matched = sum(1 for t in tokens if re.search(re.escape(t), summary, re.IGNORECASE))
            if matched >= max(2, len(tokens) // 2):
                hit = mid
                break
        c["dedupe_hit"] = hit
        out.append(c)
    return out


def r031_advice(candidates: list[dict]) -> dict:
    """给 curator 一个"落盘建议"——按 kind 分组、应用 R031 上限选 top-K by confidence。"""
    LIMITS = {"memory": 3, "skill": 1, "rule_proposal": 1, "case": 1}
    # memory = fact + lesson + pitfall + preference
    mem_candidates = [c for c in candidates if c["kind"] in ("fact", "lesson", "pitfall", "preference")]
    rule_candidates = [c for c in candidates if c["kind"] == "rule"]
    wiki_appends = [c for c in candidates if c["kind"] == "wiki-append"]

    def pick(xs, limit):
        rank = {"high": 3, "medium": 2, "low": 1}
        xs = sorted(xs, key=lambda c: -rank.get(c.get("confidence", "low"), 0))
        picked, left = [], []
        for c in xs:
            (picked if len(picked) < limit else left).append(c)
        return picked, left

    mem_picked, mem_left = pick(mem_candidates, LIMITS["memory"])
    rule_picked, rule_left = pick(rule_candidates, LIMITS["rule_proposal"])

    return {
        "memory_to_land": mem_picked,
        "memory_deferred": mem_left,
        "rule_proposal_to_land": rule_picked,
        "rule_proposal_deferred": rule_left,
        "wiki_appends": wiki_appends,  # 没硬上限
        "skill_slot_free": True,  # 此脚本不自动建议 skill
        "case_slot_used_by": "本次 consolidation 的 case 必须由 curator 写（slot=1）",
    }


# ─── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", type=str, help="trace 文件路径（默认读 stdin）")
    ap.add_argument("--slug", type=str, default=None, help="case slug 建议（默认 auto）")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非人读表格")
    args = ap.parse_args()

    if args.trace:
        text = Path(args.trace).read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            print("[curate] 等待 stdin trace 输入（Ctrl-D 结束），或用 --trace file.md")
            return 1
        text = sys.stdin.read()

    if not text.strip():
        print("[curate] trace 为空。")
        return 1

    # 扫
    existing_ids = load_memory_ids()
    entities = load_wiki_entities()
    raw = scan_kinds(text)
    wiki_hits = detect_wiki_mentions(text, entities)
    raw_with_dedupe = dedupe_memory(raw, existing_ids)
    candidates = raw_with_dedupe + wiki_hits
    counts: dict = {}
    for c in candidates:
        counts[c["kind"]] = counts.get(c["kind"], 0) + 1
    advice = r031_advice(candidates)

    today = dt.date.today().isoformat()
    slug = args.slug or "auto-curated"
    case_candidate = {
        "slug": slug,
        "date": today,
        "title": f"[AUTO] {slug}",
        "path_suggestion": f"cases/{today}-{slug}.md",
    }

    report = {
        "case_candidate": case_candidate,
        "counts_by_kind": counts,
        "dedupe_hits_in_memory": sum(1 for c in candidates if c.get("dedupe_hit")),
        "wiki_targets_mentioned": [c["target_id"] for c in wiki_hits],
        "r031_advice": advice,
        "candidates": candidates,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    # 人读模式
    print(f"=== Curator Candidate Report ({today}) ===")
    print(f"case 建议: {case_candidate['path_suggestion']}")
    print(f"总候选: {len(candidates)} 条；分布: {counts}")
    print(f"memory 重复命中: {report['dedupe_hits_in_memory']} 条 (已存在于 memory/INDEX)")
    if wiki_hits:
        print(f"wiki 实体命中: {', '.join(c['target_id'] for c in wiki_hits)}")

    print("\n-- R031 落盘建议 --")
    print(f"  memory 落 {len(advice['memory_to_land'])} 条，挤掉 {len(advice['memory_deferred'])} 条：")
    for c in advice["memory_to_land"]:
        flag = f" [已存在 {c['dedupe_hit']}]" if c.get("dedupe_hit") else ""
        print(f"    [{c['confidence']:>6}] {c['kind']:>10} · {c['summary']}{flag}")
    if advice["memory_deferred"]:
        print(f"  (deferred — 证据不足或超配额；保留到下次)")
        for c in advice["memory_deferred"]:
            print(f"    · {c['kind']}: {c['summary'][:80]}")

    if advice["rule_proposal_to_land"]:
        print(f"\n  rule_proposal 落 {len(advice['rule_proposal_to_land'])} 条：")
        for c in advice["rule_proposal_to_land"]:
            print(f"    [{c['confidence']:>6}] {c['summary']}")

    if wiki_hits:
        print(f"\n  wiki-append 候选（不计 R031）：")
        for c in wiki_hits:
            print(f"    · {c['target_id']} @ {c['target_path']} (命中 '{c['matched_name']}')")

    print("\n[curate] 本脚本只给候选，实际落盘由 curator agent 决定。加 --json 拿结构化输出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
