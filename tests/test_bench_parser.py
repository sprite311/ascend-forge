#!/usr/bin/env python3
"""
Smoke tests for tools/bench.py::parse_yaml_simple（Wave 8.2）。

和 `test_common.py` 一样：零依赖、自实现 runner。

为什么给这个 parser 加测试？
  - `bench/golden-questions.yaml` 已经涨到 32 题；这个 parser 是
    Ascend-Forge 第二个手写 YAML 子集 parser，和 `_common.py::parse_frontmatter`
    不共享实现。
  - Wave 6 扩 golden 集时，曾因缩进宽度改 4 → 2 空格导致此 parser 静默丢题。
    当前正则 `^\s{4,}` 是硬门槛，正是 Wave 7 复盘里"后续"列表里留下的"没测"项。
  - bench.py 是 KPI 数据来源，数据错了比工具坏更糟糕（静默 lossy）。

覆盖范围（来自 bench 的真实 schema）：
  1. questions 外的 key 被忽略（如 meta）
  2. 每题 id/question 正确读入
  3. quoted scalar（单双引号）去引号
  4. inline list（tags: [a, b]）切分 + 去引号
  5. 注释行 / 空行 被跳过
  6. 缩进不足（< 4 空格）导致字段丢失（**记录现状的回归测试**，不代表理想）
  7. 空输入安全
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from bench import parse_yaml_simple  # noqa: E402


# ─── 极简 runner（与 test_common.py 同款） ────────────────────────────

_PASSED = 0
_FAILED: list[tuple[str, str]] = []


def _check(name: str, cond: bool, msg: str = "") -> None:
    global _PASSED
    if cond:
        _PASSED += 1
        if "-v" in sys.argv:
            print(f"  ✅ {name}")
    else:
        _FAILED.append((name, msg))
        print(f"  ❌ {name}  {msg}")


# ─── 测试用例 ────────────────────────────────────────────────────────


def test_ignores_non_questions_top_level():
    """顶层非 questions 的 key（如 meta / version）会被丢。这是当前行为。"""
    text = """meta: some-meta
version: 1
questions:
  - id: q1
    question: hello
"""
    data = parse_yaml_simple(text)
    _check("top-level: 只保留 questions key",
           list(data.keys()) == ["questions"], f"got keys {list(data.keys())}")
    _check("top-level: questions 有 1 题", len(data["questions"]) == 1)


def test_simple_two_questions():
    text = """questions:
  - id: q1
    question: "第一题"
    expected_subagent: tuner
  - id: q2
    question: "第二题"
    expected_subagent: diagnoser
"""
    data = parse_yaml_simple(text)
    qs = data["questions"]
    _check("2-q: 题数 = 2", len(qs) == 2, f"got {len(qs)}")
    _check("2-q: q1.id", qs[0]["id"] == "q1")
    _check("2-q: q1.question 去双引号", qs[0]["question"] == "第一题",
           f"got {qs[0].get('question')!r}")
    _check("2-q: q2.expected_subagent", qs[1]["expected_subagent"] == "diagnoser")


def test_quoted_scalars():
    """双引号 / 单引号均应被剥离。"""
    text = """questions:
  - id: qA
    question: "带双引号"
    expected_subagent: 'tuner'
  - id: qB
    question: '单引号也行'
    expected_subagent: diagnoser
"""
    qs = parse_yaml_simple(text)["questions"]
    _check("quote: 双引号剥", qs[0]["question"] == "带双引号")
    _check("quote: 单引号剥（scalar）", qs[0]["expected_subagent"] == "tuner")
    _check("quote: 单引号剥（question）", qs[1]["question"] == "单引号也行")


def test_inline_list_tags():
    text = """questions:
  - id: q1
    question: x
    tags: [routing, adversarial]
  - id: q2
    question: y
    tags: ["a", 'b', c]
"""
    qs = parse_yaml_simple(text)["questions"]
    _check("inline-list: q1.tags", qs[0]["tags"] == ["routing", "adversarial"],
           f"got {qs[0].get('tags')}")
    _check("inline-list: q2.tags 混合引号", qs[1]["tags"] == ["a", "b", "c"],
           f"got {qs[1].get('tags')}")


def test_comments_and_blanks_skipped():
    text = """# 顶层注释
questions:
  # 段落注释
  - id: q1
    question: first

  - id: q2
    # 题内注释
    question: second
"""
    qs = parse_yaml_simple(text)["questions"]
    _check("comments: 2 题", len(qs) == 2, f"got {len(qs)}")
    _check("comments: q1.question", qs[0]["question"] == "first")
    _check("comments: q2.question", qs[1]["question"] == "second")


def test_empty_input_safe():
    _check("empty: 空串", parse_yaml_simple("") == {"questions": []})
    _check("empty: 仅顶层 questions",
           parse_yaml_simple("questions:\n") == {"questions": []})
    _check("empty: 无 questions key",
           parse_yaml_simple("meta: x\n") == {"questions": []})


def test_indent_threshold_quirk():
    """
    **当前行为记录测试**（不是理想设计）：
    parser 用 `^\\s{4,}` 识别子字段；因此 2 空格缩进会丢字段。

    这条测试的目的不是"验证好设计"，而是"留存活文档"：
    以后谁改 indent 阈值，请顺手看这条。Wave 6 曾踩过这个坑。
    """
    # 4 空格缩进：正常
    text_4sp = """questions:
  - id: q1
    question: four-space
"""
    qs4 = parse_yaml_simple(text_4sp)["questions"]
    _check("indent-4sp: question 被解析", qs4[0].get("question") == "four-space",
           f"got {qs4[0]!r}")
    # 2 空格缩进（挂在 `-` 开头行之后）：当前会丢
    text_2sp = """questions:
  - id: q2
  question: lost
"""
    qs2 = parse_yaml_simple(text_2sp)["questions"]
    # 当前实现会丢 question 字段——这是"仪表盘"测试，记录现状
    _check("indent-2sp: question 字段在 2 空格时丢失（记录现状）",
           "question" not in qs2[0],
           f"got {qs2[0]!r}  ← 如果这条开始 fail，说明有人改了 indent 阈值，好事，"
           f"顺手 update 本测试")


def test_real_golden_file_parses():
    """最关键的 smoke：仓库里真的 golden-questions.yaml 能被 parser 读完。"""
    gold = ROOT / "bench" / "golden-questions.yaml"
    if not gold.exists():
        _check("golden-file: 存在", False, f"no {gold}")
        return
    text = gold.read_text(encoding="utf-8")
    data = parse_yaml_simple(text)
    qs = data["questions"]
    _check("golden-file: 题数 >= 15", len(qs) >= 15, f"got {len(qs)}")
    # 每题必须至少有 id + question + expected_subagent（bench.py 依赖的三字段）
    missing_id = [i for i, q in enumerate(qs) if "id" not in q]
    missing_q = [i for i, q in enumerate(qs) if "question" not in q]
    missing_e = [i for i, q in enumerate(qs) if "expected_subagent" not in q]
    _check("golden-file: 所有题都有 id", not missing_id,
           f"miss {missing_id}")
    _check("golden-file: 所有题都有 question", not missing_q,
           f"miss {missing_q}")
    _check("golden-file: 所有题都有 expected_subagent", not missing_e,
           f"miss {missing_e}")


# ─── Entry ────────────────────────────────────────────────────────────


def main() -> int:
    print("=== test_bench_parser.py ===")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except Exception as e:
                _FAILED.append((name, f"raised {type(e).__name__}: {e}"))
                print(f"  ❌ {name}  raised: {e}")
    print()
    print(f"通过 {_PASSED} · 失败 {len(_FAILED)}")
    if _FAILED:
        print("\n失败详情：")
        for n, m in _FAILED:
            print(f"  · {n}  {m}")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
