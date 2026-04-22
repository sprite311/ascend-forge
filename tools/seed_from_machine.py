#!/usr/bin/env python3
"""
从当前机器读硬件 / 驱动 / CANN / Python 三件套版本，输出一份 `memory/facts/seed-<host>-env.md`
+ 更新 `wiki/hardware/<id>.md` 的 `last_verified`。

设计原则：
  - 只读：任何写入都先 dry-run；加 --apply 才落盘；默认 diff 打印。
  - 容错：不是昇腾机时 graceful，输出 "N/A（非 Ascend 环境）" 而非崩溃。
  - 不造假：任何探测不到的值填 "UNKNOWN" 而不是猜。

用法：
  python3 tools/seed_from_machine.py              # 打印探测结果 + 待写的 facts md
  python3 tools/seed_from_machine.py --apply      # 写 memory/facts/seed-<host>-env.md
  python3 tools/seed_from_machine.py --hardware 910b   # 同时更新 wiki/hardware/910b.md last_verified
"""
from __future__ import annotations
import argparse
import datetime as dt
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], timeout: int = 5) -> str:
    try:
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, text=True, timeout=timeout
        )
        return out.strip()
    except FileNotFoundError:
        return ""
    except subprocess.TimeoutExpired:
        return f"[timeout:{' '.join(cmd)}]"
    except subprocess.CalledProcessError as e:
        return (e.output or "").strip() or f"[fail:{' '.join(cmd)}]"


def detect() -> dict:
    info = {
        "host": socket.gethostname(),
        "os_kernel": platform.release(),
        "os_arch": platform.machine(),
        "os_release": "",
        "driver_version": "UNKNOWN",
        "cann_version": "UNKNOWN",
        "npu_smi_exists": bool(shutil.which("npu-smi")),
        "npu_count": "UNKNOWN",
        "npu_model": "UNKNOWN",
        "npu_health": "UNKNOWN",
        "python_version": platform.python_version(),
        "pytorch_version": "N/A",
        "torch_npu_version": "N/A",
        "torch_npu_available": "N/A",
    }

    # OS
    try:
        with open("/etc/os-release") as f:
            rel = {}
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    rel[k] = v.strip('"')
            info["os_release"] = f"{rel.get('NAME','?')} {rel.get('VERSION','?')}"
    except Exception:
        info["os_release"] = "UNKNOWN"

    # 驱动
    drv = Path("/usr/local/Ascend/driver/version.info")
    if drv.exists():
        info["driver_version"] = drv.read_text(encoding="utf-8").strip().replace("\n", " | ")

    # CANN
    cann = Path("/usr/local/Ascend/ascend-toolkit/latest/version.cfg")
    if cann.exists():
        info["cann_version"] = cann.read_text(encoding="utf-8").strip().replace("\n", " | ")

    # npu-smi
    if info["npu_smi_exists"]:
        smi = run(["npu-smi", "info"])
        if smi:
            # 粗略数：计数形如 " 0 ... OK ..."  开头是 NPU index 的行
            rows = [l for l in smi.splitlines()
                    if re.match(r"\s*\|\s*\d+\s+", l) and "Health" not in l]
            info["npu_count"] = len(rows) if rows else "UNKNOWN"
            # 型号从 product 查
            prod = run(["npu-smi", "info", "-t", "product", "-i", "0"])
            for line in prod.splitlines():
                if "Product" in line and ":" in line:
                    info["npu_model"] = line.split(":", 1)[1].strip()
                    break
            info["npu_health"] = "查看 `npu-smi info` 输出确认"
        else:
            info["npu_count"] = 0

    # Python torch / torch_npu
    py = shutil.which("python3") or shutil.which("python")
    if py:
        r = run([py, "-c",
                 "import torch,torch_npu;print(torch.__version__);print(torch_npu.__version__);print(torch.npu.is_available())"],
                timeout=15)
        lines = r.splitlines()
        if len(lines) >= 3 and "Error" not in r and "Traceback" not in r and "[fail" not in r and "[timeout" not in r:
            info["pytorch_version"], info["torch_npu_version"], info["torch_npu_available"] = lines[0], lines[1], lines[2]
        else:
            # try torch alone
            r2 = run([py, "-c", "import torch;print(torch.__version__)"], timeout=10)
            bad_markers = ("[", "Traceback", "ModuleNotFoundError", "ImportError", "Error")
            if r2 and not any(m in r2[:40] for m in bad_markers):
                info["pytorch_version"] = r2.splitlines()[0]
    return info


def render_facts_md(info: dict) -> str:
    today = dt.date.today().isoformat()
    body = f"""---
id: seed-{info['host']}-env-{today}
kind: fact
tags: [environment, seed, {info['host']}, auto-generated]
source: seed_from_machine.py@{info['host']}
created_at: {today}
verified_at: {today}
confidence: high
ttl_days: 60
related_wiki: [cann, torch-npu]
---

## 本机环境快照（由 `tools/seed_from_machine.py` 自动采集）

| 项                   | 值 |
|----------------------|----|
| Host                 | `{info['host']}` |
| OS                   | {info['os_release']} |
| Kernel               | `{info['os_kernel']}` |
| Arch                 | `{info['os_arch']}` |
| NPU Driver           | `{info['driver_version']}` |
| CANN (toolkit)       | `{info['cann_version']}` |
| NPU 数量 (npu-smi)   | `{info['npu_count']}` |
| NPU Product          | `{info['npu_model']}` |
| Python               | `{info['python_version']}` |
| PyTorch              | `{info['pytorch_version']}` |
| torch_npu            | `{info['torch_npu_version']}` |
| torch.npu.is_available() | `{info['torch_npu_available']}` |

> 本条随 ttl 60 天过期；下次跑 `seed_from_machine.py --apply` 会刷新或生成新版本。
> 值为 `UNKNOWN` 意味着探测工具不可用——不等于"没装"，只是探不出。

## 下一步建议
1. 对照 `wiki/software/cann.md` 的三件套矩阵确认当前组合是否在官方推荐范围内。
2. 若 `torch.npu.is_available()` 不是 True，走 `wiki/playbooks/general-debug.md` Step 1–2。
3. 把 `NPU Product` 字段的结果回填到对应 `wiki/hardware/<id>.md` 的"规格"段（覆盖 TBD）。
"""
    return body


def update_hardware_verified(hw_id: str, dry_run: bool) -> bool:
    p = ROOT / "wiki" / "hardware" / f"{hw_id}.md"
    if not p.exists():
        print(f"[seed] ⚠️ wiki/hardware/{hw_id}.md 不存在，跳过 last_verified 更新。")
        return False
    text = p.read_text(encoding="utf-8")
    today = dt.date.today().isoformat()
    new_text = re.sub(
        r"^(last_verified:\s*).*$",
        rf"\g<1>{today}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if new_text == text:
        return False
    if dry_run:
        print(f"[seed] (dry) 将更新 {p} last_verified → {today}")
        return True
    p.write_text(new_text, encoding="utf-8")
    print(f"[seed] ✏️  {p} last_verified → {today}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写 memory/facts/...md")
    ap.add_argument("--hardware", type=str, default=None, help="同时刷新 wiki/hardware/<id>.md last_verified")
    args = ap.parse_args()

    info = detect()

    print("=== 环境探测结果 ===")
    for k, v in info.items():
        print(f"  {k:>22}: {v}")

    md = render_facts_md(info)
    today = dt.date.today().isoformat()
    target = ROOT / "memory" / "facts" / f"seed-{info['host']}-env-{today}.md"

    print("\n=== 将写入 memory fact ===")
    print(f"  路径: {target}")
    print(f"  行数: {len(md.splitlines())}")

    if args.apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(md, encoding="utf-8")
        print(f"[seed] ✏️  wrote {target}")
    else:
        print("[seed] 加 --apply 真正写入。")
        print("  --- preview ---")
        for line in md.splitlines()[:12]:
            print(f"  {line}")
        print("  --- (truncated) ---")

    if args.hardware:
        update_hardware_verified(args.hardware, dry_run=not args.apply)

    return 0


if __name__ == "__main__":
    sys.exit(main())
