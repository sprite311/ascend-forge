---
id: policy-checker-task-boundary
proposed_at: 2026-04-20
evidence:
  - case/2026-04-20-wave3-tooling
status: pending   # pending|accepted|rejected|superseded
proposed_by: knowledge-curator
applies_to: [tools/check_policy.py, knowledge-curator, CI]
---

## 规则
`tools/check_policy.py` 必须支持按 **commit 边界** 切分"一次任务"的产出。
具体：新增 `--since <commit-ish>` 参数；不指定时默认退回 `git status`
（现状），指定时按 `git diff --name-only <commit-ish>..HEAD` 统计。

R031 单任务配额（memory≤3 / skill≤1 / rule_proposal≤1 / case≤1）按
`--since` 的区间判定，不再把多次任务的累积工作区当作"一次任务"。

## 理由
Wave 3 end-to-end 跑 `check_policy.py --from-git` 时误报 7 条违规：
`memory=4>3, case=3>1` 等。真实情况是 Wave 1 / Wave 2 / Wave 3 三次独立任务的
未 commit 产物合并在工作区里。现有 policy checker 不会漂白这种情况，会**在 CI 里
持续误报**，直接让人学会忽略警告——这比没有 policy 还糟。

另两个 `tools/` 下的 R021 违例同样因边界问题而误报。工具链建设本身不适用
`write_whitelist`（agent 正常运行不会写 `tools/`）；可以通过"引导期 commit" 边界
自然豁免。

## 实施草案
```python
# tools/check_policy.py
ap.add_argument("--since", help="commit-ish; 仅统计 HEAD..<since> 的差异")
...
if args.since:
    writes = subprocess.check_output(
        ["git", "diff", "--name-only", f"{args.since}..HEAD"],
        cwd=ROOT, text=True,
    ).splitlines()
elif args.from_git:
    writes = git_changed_files()  # 现有实现
```

CI 用法：在每次 PR 的 diff（`origin/main..HEAD`）上跑。

## 证据门槛
当前仅 1 case（本 Wave 误报）。按 R032 需要 ≥3 独立 case 自动晋升，否则待用户
`/rules promote` 手动确认。

可能的新证据来源：
- 未来在 `cases/*.md` 里出现"policy 误报导致我手动豁免"的任何记录；
- CI 中积累的误报统计（若接入后观察到 >30% 误报率可直接 promote）。

## 生效范围
`tools/check_policy.py`；间接影响 `.agent/evolution_policy.md` 的操作化定义（需在该文档里注明
"单任务"=`--since` 区间，默认工作区）。
