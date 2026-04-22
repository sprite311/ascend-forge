---
id: pitfall-cross-session-state-amnesia
date: 2026-04-22
tags: [self-reflection, session, ground-truth, ls-before-claim, concurrent-sessions]
status: active
source: case/2026-04-22-wave8
ttl_days: 365
verified_at: 2026-04-22
---

# Pitfall：跨 session "失忆" + "定时自检副 session" 并发导致的状态假设错误

## 现象

Wave 8 close 时我写下：
> "`skills/` 目录下 0 个真用于迁移/部署/调优的可跑 playbook"
> "skills: 0（明确识别为最大缺口）"

**真实状态**：
- `ls skills/` 有 **12 个** skill 目录，每个都有 SKILL.md（40-128 行）；其中
  - 11 个是 **bootstrap** 创建（首次 commit 里就有，model-adaptation / mindie-deployment / msprof-profiling / ...）；
  - **1 个** `wiki-consolidate-draft-to-stable/` 是**另一个 Claude session**在 2026-04-22 09:44 创建的——那个 session 是我之前挂的 10 分钟 scheduled-task fire 触发的副线程，做完了我本应做的 Wave 9.1。

**我的判断错了两处**：
1. "skills 为空"在事实上是错的——bootstrap 里本来就有 11 个；
2. 没意识到自己挂的 scheduled-task 正在产出真实文件；整个 Wave 8 反思基于一个**过期的 compaction summary**，而不是**`ls` 当前真相**。

## 根因

三层叠加：

1. **Summary-driven amnesia**：会话被 compaction 后，我接着读"prior summary"，里面写的是"L4 为空 / skills: 0"。这句话可能来自某个更早 session 的片段，也可能是我自己某次草率断言被截进 summary。**我没 verify**——直接把它当事实复用到 Wave 8 反思里。

2. **"副 session"并发盲区**：我自己在 Wave 7 创建的 `ascend-forge-continue-check` scheduled task（10 分钟后触发）**真的触发了**，真的有另一个 Claude session 执行了工作，真的落盘了 skill 文件。但**我的 session 上下文里没有任何通知**说"副 session 已完成 X 任务"。两条时间线各自演进，互不感知。

3. **从不先 `ls`**：写反思时习惯性引用"我记得 skills 为空"，而不是敲一次 `ls skills/ | wc -l`。**架构批判性文字尤其要有事实支撑**——否则就是"有腔调、无依据"的自以为是。

## 成本

- Wave 8 close case 里的"skills: 0 → 最大缺口 → Wave 9 第一件事补 L4"的**整条推理链基于错误事实**；虽然结论"需要更多可执行脚本"仍大致对（skills/*/SKILL.md 是文档非脚本），但**强度被夸大了一个数量级**（12→0 vs 12→30 完全不同）。
- 用户看到我自信地宣布"只会回忆、不会动手"，会误以为问题比实际严重。**削弱信号可信度**的代价比事实错误本身大。

## 缓解策略

### 策略 A：写任何"量化架构断言"前先 ls（零成本，立刻做）

每次要写 "X 层空 / Y 目录 0 条 / Z 有 N 个" 前，**必须跑一次 ls 或 grep 或 glob**。规则：

> **不用工具数出来的数字，不写进 case/lesson/critique**。

模板（写反思的人自查）：
- 断言 "skills 为空" → 先 `ls skills/` / `find skills -name SKILL.md | wc -l`
- 断言 "tests 覆盖 N 条" → 先 `python3 tests/run_all.py`
- 断言 "memory 过期 N 条" → 先 `python3 tools/evolve.py` 看 Summary

### 策略 B：副 session 产出必须对账（未来做）

本仓库将来会有多处 scheduled-task / 并发 session，需要一个"增量对账"工具：

```bash
# 设想
python3 tools/session_delta.py --since <last-session-end>
# 输出：distance this session 开始前 vs 现在，哪些文件新增/修改/删除
```

当前方案近似：`git status --porcelain` 列出所有未 commit 变更——但这只对"有 git 的仓"有效，且不区分"我刚做的" vs "另一个 session 做的"。需要 session 时间戳标记。Wave 9+ 考虑。

### 策略 C：compaction summary 不可信，必须 re-verify（规则层）

提议 **R035**：

> 会话被 compaction / 继续时，主 agent 不得直接引用 summary 里的数值性断言。
> 任何定量描述（"N 个 skill"、"M 条 memory"、"0 个 X"）在重新落盘前，
> 必须被一次工具调用（ls/grep/evolve）覆写。

成本：每次继续会话多 1-2 个 ls 调用。收益：避免 "整段反思基于过期事实" 的大坑。

## 相关

- `cases/2026-04-22-wave8.md` — 错的那段反思（Wave 8 close 附录已追加修正）
- `memory/lessons/lesson-architecture-critique.md` #11 — 已被修正
- `rules/proposals/2026-04-22-case-must-produce-skill-or-skip-reason.md` — 提案立意仍成立，但 evidence 节奏变了
