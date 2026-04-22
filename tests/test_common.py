#!/usr/bin/env python3
"""
Smoke tests for tools/_common.py.

无第三方依赖（不依赖 pytest）；用 assert + 自实现 runner。
跑法：
    python3 tests/test_common.py
    python3 tests/test_common.py -v        # 每条测试都打印

为什么不用 pytest？
  - Ascend-Forge 的部署目标是"在用户机器上开箱即跑"，pytest 是一层不必要的依赖。
  - 这些测试跑在 CI 里（GitHub Actions）也不需要装任何东西。
  - 若将来测试数上到 20+，再评估加 pytest。

覆盖面（最小集，来自 Wave 3 / 5 的真实踩坑）：
  1. parse_frontmatter：inline comment 剥离
  2. parse_frontmatter：inline comment 不误伤 URL fragment (#anchor)
  3. parse_frontmatter：multi-line block list 收集
  4. parse_frontmatter：inline list `[a, b]`
  5. parse_frontmatter：无 frontmatter 返回 {}
  6. strip_frontmatter：去掉 frontmatter 剩正文
  7. strip_frontmatter：无 frontmatter 原样返回
  8. iter_cases：能读到 cases/ 下 *.md
"""
from __future__ import annotations

import sys
from pathlib import Path

# 让 tests/ 里能 import tools._common（反之亦然）
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from _common import (  # noqa: E402
    parse_frontmatter,
    strip_frontmatter,
    iter_cases,
    FRONTMATTER_RE,
    ROOT as COMMON_ROOT,
)


# ─── 极简 runner ───────────────────────────────────────────────────────

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


# ─── 测试用例 ──────────────────────────────────────────────────────────


def test_parse_fm_inline_comment():
    """inline comment（` # note`）必须被剥掉，仅当 `#` 前是空白。"""
    text = """---
status: pending   # 这是注释
id: foo
---

body
"""
    fm = parse_frontmatter(text)
    _check("inline-comment: status 剥掉注释", fm.get("status") == "pending",
           f"got {fm.get('status')!r}")
    _check("inline-comment: id 正常", fm.get("id") == "foo", f"got {fm.get('id')!r}")


def test_parse_fm_url_fragment_protected():
    """URL 里的 `#fragment`（前面没空格）不应被当作注释剥掉。"""
    text = """---
link: https://example.com/doc#section-3
anchor: page.html#top
---

body
"""
    fm = parse_frontmatter(text)
    _check(
        "url-fragment: 带 #section-3 的 URL 完整保留",
        fm.get("link") == "https://example.com/doc#section-3",
        f"got {fm.get('link')!r}",
    )
    _check(
        "url-fragment: page.html#top 完整保留",
        fm.get("anchor") == "page.html#top",
        f"got {fm.get('anchor')!r}",
    )


def test_parse_fm_multiline_block_list():
    """多行 block list（`sources:\\n  - X\\n  - Y`）必须收集成 list。"""
    text = """---
id: demo
sources:
  - https://a.example.com
  - https://b.example.com
  - skill/foo/SKILL.md
tags: [x, y]
---

body
"""
    fm = parse_frontmatter(text)
    _check("block-list: sources 是 list", isinstance(fm.get("sources"), list))
    _check("block-list: sources 长度 3", len(fm.get("sources", [])) == 3,
           f"got {fm.get('sources')}")
    _check("block-list: 第一条正确",
           fm.get("sources", ["?"])[0] == "https://a.example.com")
    _check("block-list: block list 之后的 tags 不被吞", fm.get("tags") == ["x", "y"])


def test_parse_fm_inline_list():
    text = """---
tags: [a, b, c]
aliases: ["Q", 'R']
---
"""
    fm = parse_frontmatter(text)
    _check("inline-list: tags", fm.get("tags") == ["a", "b", "c"])
    _check("inline-list: aliases 去引号", fm.get("aliases") == ["Q", "R"])


def test_parse_fm_empty_returns_empty_dict():
    _check("no-frontmatter: 空串 → {}", parse_frontmatter("") == {})
    _check("no-frontmatter: 纯正文 → {}",
           parse_frontmatter("# Hello\n\nsome text.\n") == {})
    _check("no-frontmatter: 半开 frontmatter → {}",
           parse_frontmatter("---\nid: x\n# 没有结束 ---\n") == {})


def test_strip_frontmatter():
    text = "---\nid: x\n---\n\n# Body\n\ncontent"
    out = strip_frontmatter(text)
    _check("strip-fm: body 保留", "# Body" in out)
    _check("strip-fm: frontmatter 去掉", "id: x" not in out)


def test_strip_frontmatter_no_fm():
    text = "# Just body\nno frontmatter\n"
    _check("strip-fm: 无 frontmatter 原样", strip_frontmatter(text) == text)


def test_iter_cases_yields_tuples():
    """iter_cases 应迭代 cases/*.md 返回 (path, text)。仓库里必有 case。"""
    cases = list(iter_cases())
    _check("iter_cases: 至少有 1 条", len(cases) >= 1, f"got {len(cases)}")
    if cases:
        p, t = cases[0]
        _check("iter_cases: yield 的是 Path", isinstance(p, Path))
        _check("iter_cases: yield 的是 str", isinstance(t, str))


def test_root_is_repo_root():
    _check("ROOT: 是 Path", isinstance(COMMON_ROOT, Path))
    _check("ROOT: 包含 tools/", (COMMON_ROOT / "tools").is_dir())
    _check("ROOT: 包含 rules/ACTIVE.md", (COMMON_ROOT / "rules" / "ACTIVE.md").exists())


def test_frontmatter_re_matches():
    _check("FRONTMATTER_RE: 能匹配标准 frontmatter",
           FRONTMATTER_RE.match("---\nid: x\n---\nbody") is not None)
    _check("FRONTMATTER_RE: 不匹配纯 body",
           FRONTMATTER_RE.match("body only") is None)


# ─── Entry ─────────────────────────────────────────────────────────────


def main() -> int:
    print("=== test_common.py ===")
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
