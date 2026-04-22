#!/usr/bin/env python3
"""
极简 test 聚合 runner（Wave 8.3）。

跑法：
    python3 tests/run_all.py            # 简洁摘要
    python3 tests/run_all.py -v         # 每条测试都打印

为什么不上 pytest？
  - Wave 7 定了"纯 stdlib"原则；runner 本身只有 30 行。
  - 每个 test_*.py 都能独立 `python3 tests/test_xxx.py` 跑，
    这里只是汇总入口，不替代独立跑法。

扩展：
  新增 tests/test_*.py 无需改本文件——glob 自动发现。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def main() -> int:
    files = sorted(HERE.glob("test_*.py"))
    if not files:
        print("（无测试文件）")
        return 0
    print(f"=== Ascend-Forge test runner · {len(files)} suites ===\n")
    failed: list[str] = []
    for f in files:
        print(f"▶ {f.name}")
        rc = subprocess.call([PY, str(f)] + (["-v"] if "-v" in sys.argv else []),
                             cwd=HERE.parent)
        if rc != 0:
            failed.append(f.name)
        print()
    print("=" * 50)
    if failed:
        print(f"❌ {len(failed)}/{len(files)} 套件失败：{', '.join(failed)}")
        return 1
    print(f"✅ 全部 {len(files)} 套件通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
