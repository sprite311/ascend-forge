#!/usr/bin/env python3
"""
共享工具库（tools/_common.py）。

把 `tools/*.py` 里重复 4 遍的 frontmatter 解析器、ROOT 常量、banner 打印
合并到这一个文件，保证：
  - YAML parser 只有一份，bug fix 一次即可全员受益；
  - 每个工具 `from _common import ROOT, parse_frontmatter, ...` 即可；
  - 工具间口径统一（如 evidence 计数的 case 扫描方式）。

历史原因：骨架阶段为了让每个 tool 自包含，parse_fm 被复制了 4 次，
连 inline-comment bug 和 multi-line block-list bug 都各修了 3 次（见
`cases/2026-04-20-wave3-tooling.md`）。这是典型的 DRY 违反；Wave 5 反思
阶段决定抽公共。

设计边界：
  - 只放"跨 3+ 工具使用"的东西；单一工具专用逻辑保留在本地。
  - 不引第三方依赖；保持纯 stdlib，兼容沙箱。
  - 不 re-export argparse/subprocess 等 stdlib；工具自己 import。

公共 API：
  - ROOT                  → 仓库根目录 Path
  - FRONTMATTER_RE        → YAML frontmatter 匹配
  - parse_frontmatter(t)  → dict；支持 inline comment 剥离 + 多行 block list
  - strip_frontmatter(t)  → 去掉首部 frontmatter 的正文
  - banner(title)         → 打印章节分隔线（evolve.py 用）
  - iter_cases()          → 迭代 cases/*.md 的 (path, text)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent

# 匹配文件开头的 YAML frontmatter（--- … ---）
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """解析 YAML-ish frontmatter。

    支持：
      - 标量：`key: value`
      - inline comment：`key: value  # note` → 保留 value，剥掉 `# note`
        （仅当 `#` 前是空白时才视为注释；URL fragment `#anchor` 不误伤）
      - inline list：`tags: [a, b, c]`
      - multi-line block list::

            sources:
              - https://...
              - https://...

    不支持：嵌套 mapping（用不着）、YAML 引用（`&anchor` / `*ref`）。

    调用方常见用法：
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        pid = fm.get("id", path.stem)
        status = fm.get("status", "pending")
        evidence = fm.get("evidence", [])
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict = {}
    last_list_key: str | None = None  # key whose value is a YAML block list being collected
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        # YAML block-list item：`  - value` → append to last_list_key
        stripped = raw.lstrip()
        if stripped.startswith("- ") and last_list_key is not None:
            item = stripped[2:].strip().strip('"').strip("'")
            out[last_list_key].append(item)
            continue
        if ":" not in raw:
            continue
        k, v = raw.split(":", 1)
        k, v = k.strip(), v.strip()
        # strip inline comment（仅在 `#` 前为空白时生效；避免 URL fragment 误伤）
        v = re.sub(r"\s+#.*$", "", v).strip()
        if v.startswith("[") and v.endswith("]"):
            out[k] = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            last_list_key = None
        elif v == "":
            # 空值 → 可能是 block list / 嵌套 mapping 的开端；准备收 list
            out[k] = []
            last_list_key = k
        else:
            out[k] = v.strip('"').strip("'")
            last_list_key = None
    return out


def strip_frontmatter(text: str) -> str:
    """返回去掉首部 frontmatter 的正文（若无 frontmatter 原样返回）。"""
    return FRONTMATTER_RE.sub("", text, count=1)


def banner(title: str) -> None:
    """章节分隔线（与 evolve.py 原样保持兼容）。

    先 flush 再写：当 evolve.py 调 subprocess 把子工具接到同一 stdout 时，
    不 flush 的话子进程写 fd 1 会出现在父 banner **之前**（缓冲错位）。
    """
    import sys as _sys
    _sys.stdout.flush()
    print(f"\n━━━ {title} ━━━", flush=True)


def iter_cases() -> Iterator[tuple[Path, str]]:
    """迭代 cases/*.md，yield (path, text)。读取失败的文件跳过（不抛异常）。"""
    cases_dir = ROOT / "cases"
    if not cases_dir.exists():
        return
    for p in sorted(cases_dir.glob("*.md")):
        try:
            yield p, p.read_text(encoding="utf-8")
        except Exception:
            continue


# 兼容别名：部分老代码用 parse_fm
parse_fm = parse_frontmatter
