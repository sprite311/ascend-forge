---
id: pitfall-traceback-as-version
kind: pitfall
tags: [tooling, subprocess, version-detection, python, robustness]
source: case/2026-04-20-wave3-tooling
created_at: 2026-04-20
verified_at: 2026-04-20
confidence: high
ttl_days: 365
related_wiki: [torch-npu]
---

## 坑：把 subprocess 失败的输出当作"命令返回值"

### 现象
`tools/seed_from_machine.py` 在沙箱（无 torch）跑的第一版输出：

```
pytorch_version: Traceback (most recent call last):
```

原因：`run()` 函数在 `CalledProcessError` 时返回 `e.output`，调用侧把第一行当作版本号。

### 场景
任何用 `python3 -c "import X;print(X.__version__)"` 做版本探测的工具都会踩——
常见的 torch / torch_npu / transformers / deepspeed 探测都在此列。

### 正确做法
探测返回字符串 **必须过滤已知失败标记**，不能只判空：

```python
bad_markers = ("[", "Traceback", "ModuleNotFoundError",
               "ImportError", "Error")
if r and not any(m in r[:40] for m in bad_markers):
    version = r.splitlines()[0]
else:
    version = "N/A"
```

更稳妥的替代：分开跑 exit code 判失败，而不是看 stdout。但在需要跨版本、不想
hard-depend `sys.exit(1)` 的探测脚本里，做"标记过滤"是现实折中。

### 关联
- `tools/seed_from_machine.py` 已修复（2026-04-21）。
- 未来新增任何"用 `python -c` 探测"的逻辑，必须复用 `bad_markers` 列表或等价过滤。
