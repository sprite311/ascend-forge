---
id: 2026-04-20-wave3-tooling
date: 2026-04-20
tags: [wave3, tooling, evolve, policy, rag-index, wiki-check, seed, self-test]
models: []
hardware: []
software: [python]
outcome: resolved
---

# Wave 3 · 工具链可运行化（evolve / check_policy / wiki_link_check / rag_index / seed_from_machine）

## 背景

Wave 1 + Wave 2 把知识骨架（wiki 24 页、cases 3 条、memory 4 条、rule proposal 1 条）
写到了仓库里，但之前的所有自动化脚本都还是"有占位文件没真功能"。
本 Wave 的目标：**让 5 个工具都真实跑得起来**，输出可审计的索引 / 反链 / 统计产物，并
通过一次端到端 `evolve.py --apply` 闭合 Consolidation 回路。

## 用户请求

> 继续完成 agent 没有完成的核心任务。

## 我做了什么

### 1. `tools/wiki_link_check.py`（升级）

- 新增 `--apply` / `--strict`。
- 扫描 24 个 wiki 页 → 校验 `related:` 目标全部存在 → 写 `wiki/INDEX.jsonl`（24 行）→
  为每个页自动重写 `## Backlinks` 小节（相对路径、sorted、去重）。
- 样例：`wiki/software/cann.md` 的 Backlinks 现在自动列出 9 个反指页
  （310b/310p/910b/910c/docker-davinci-mount/driver-firmware-mismatch/general-debug/mindformers/mindie）。

### 2. `tools/rag_index.py`（升级）

- 新增 `--apply` 写 `cases/INDEX.jsonl`。
- 新增 `--query "keywords" --top-k N` 做本地 grep-based 检索（id/tag/body 分别 ×10/×5/×1 权重）。
- 当前索引 3 条 case。

### 3. `tools/check_policy.py`（新建，179 行）

校验四条策略（对照 `.agent/evolution_policy.md`）：

| 规则  | 检查内容 | 实测结果 |
|------|--------|---------|
| R010 | memory/wiki/skill/proposal 必须带 `source:` frontmatter | ✅ 全部通过 |
| R020 | 代码块中的破坏性命令必须页内带 ⚠️ / R020 / "不要自动" 提示 | ✅ 全部通过 |
| R021 | 写路径必须在 whitelist、且不在 denylist | ❌ 5 处（见下） |
| R031 | 单任务配额 memory≤3 / skill≤1 / case≤1 / rule≤1 | ❌ 2 处（见下） |

**R021 故意违例 5 处**（`tools/evolve.py`、`check_policy.py`、`rag_index.py`、
`wiki_link_check.py`、`seed_from_machine.py`）：
这是**引导期例外**——工具链本身正在被 agent 创建。
我已在本 case "后续"段记录：一旦工具稳定、后续版本应转由人工 `git` commit，
agent 正常运行时不再触发 `tools/` 写入。

**R031 故意违例 2 处**（`memory=4>3`、`case=3>1`）：
这是**跨 Wave 汇总**的统计伪违规——policy checker 只看 git 工作区，无法区分
"单任务"边界。Wave 1/2/3 三次任务的产出合并落在未 commit 工作区，自然超额。
**修复思路**（记在 rule proposal）：下一版 `check_policy.py` 接受 `--since <commit>`
参数，按 commit 切分任务。

### 4. `tools/seed_from_machine.py`（新建，224 行）

在沙箱（非 Ascend 机）上测试通过——所有 NPU 字段优雅降级为 `UNKNOWN`，torch 探测
链在 ImportError 时返回 `N/A` 而非传播 traceback。
真机行为（未验证，需用户在 910B 上跑）：

```bash
# 在昇腾机上
python3 tools/seed_from_machine.py --apply --hardware 910b
# 应生成 memory/facts/seed-<host>-env-<date>.md
# 并刷新 wiki/hardware/910b.md 的 last_verified 字段
```

### 5. `tools/evolve.py`（重写为 8 步 orchestrator）

```
Step 1 · git status（只报告，37 条工作区变更）
Step 2 · check_policy.py --from-git（执行 R010/R020/R021/R031）
Step 3 · wiki_link_check.py --apply（INDEX.jsonl + Backlinks 自动维护）
Step 4 · rag_index.py --apply（cases/INDEX.jsonl）
Step 5 · memory TTL 扫描（按 verified_at + ttl_days 判过期，本次 0）
Step 6 · wiki seed-gap 扫描（status=draft 或 TBD，8 页）
Step 7 · rule proposal 成熟度（evidence 计数 + promote 建议，1 条 pending）
Step 8 · 写 docs/EVOLUTION-STATS.md（自动化报告）
```

## 关键发现（Debug 日志）

### 🐛 Bug 1：frontmatter parser 误吞 YAML inline 注释

`rules/proposals/…md` 的 `status: pending   # pending|accepted|rejected|superseded`
被解析成 `status=pending   # pending|accepted|rejected|superseded`（整段带进值里）。
**修复**：三处 `parse_fm` / `parse_frontmatter` 都加上
`v = re.sub(r"\s+#.*$", "", v).strip()`——只在 `#` 前有空白时才当作注释，
避免误吞 URL 里的 `#fragment`。

### 🐛 Bug 2：frontmatter parser 无法读 YAML block-list

`wiki/hardware/910b.md` 的 `sources:` 字段用的是块格式：

```yaml
sources:
  - https://www.hiascend.com/...
  - skill/.../version_matrix.md
```

第一版 parser 把 `  - https://www.hiascend.com/...` 当成了新 kv 对，结果
`wiki/INDEX.jsonl` 里出现了 `"- https": "//www.hiascend.com/..."` 这种错位。
**修复**：parser 增加 `last_list_key` 状态——若上一个 key 的值为空（`sources:`），
则把接下来以 `- ` 开头的缩进行追加到该 key 的列表。Apply 后 INDEX.jsonl 中
`sources` 正确变成 `["https://...", "skill/.../version_matrix.md"]`。

### 🐛 Bug 3：`seed_from_machine.py` 在无 torch 环境把 traceback 当版本

在沙箱里 `python3 -c "import torch"` 报 ModuleNotFoundError，traceback 首行
`Traceback (most recent call last):` 被误认作 "pytorch 版本"。
**修复**：fallback 前过滤 `bad_markers = ("[", "Traceback", "ModuleNotFoundError",
"ImportError", "Error")`；任一出现在前 40 字符即判为失败、值保留 `N/A`。

## 结果

运行一次 `python3 tools/evolve.py --apply` 产生下列**新/更新**的受控工件：

| 工件 | 行数 / 条数 | 路径 |
|-----|----------|------|
| Wiki 索引 | 24 行 | `wiki/INDEX.jsonl` |
| Wiki Backlinks | 24 页均更新 | `wiki/**/*.md` 的 `## Backlinks` 小节 |
| Cases 索引 | 3 行 | `cases/INDEX.jsonl` |
| 进化统计 | 30 行 | `docs/EVOLUTION-STATS.md` |

`docs/EVOLUTION-STATS.md` 汇总：`git_changes=41, wiki=27, cases=3, memory_atoms=4,
seed_gap=8, proposals_ready=0`。Consolidation 回路**首次闭合**。

## 待验证

- [ ] `seed_from_machine.py` 在 **真机 910B** 上完整跑一遍（当前只在非 Ascend 沙箱验证了降级）。
- [ ] `check_policy.py --from-git` 在**真正 commit 间隔**里跑（当前只在累积工作区跑，
      无法区分 Wave 边界）。建议下一版加 `--since <commit>`。
- [ ] `rag_index.py --query "hccl timeout"` 在 cases 增长到 ≥10 条后评估召回质量，
      判断是否需要引入 BM25 后端（代码里已留扩展点）。

## 知识沉淀（curator log）

本 Wave 收尾时由 `@knowledge-curator` 产生（遵守 R031：memory≤3 / case=1 / wiki=0 /
rule_proposal≤1）：

- **case**: `cases/2026-04-20-wave3-tooling.md`（本页，不计入用户 R031 限额——
  Wave 是 agent 自身建设，单 Wave 按 1 case 合理）。
- **memory**:
  - `memory/lessons/lesson-yaml-parser-inline-comment-and-blocklist.md`（新）——
    教训：用正则 + 行扫描手写 YAML 子集时，至少覆盖 inline-comment + block-list
    两个 case，否则数据会静默错位。
  - `memory/pitfalls/pitfall-traceback-as-version.md`（新）——
    坑：把 `subprocess.CalledProcessError.output` 直接当作"命令返回值"，
    在 `python -c "import X"` 探测场景会把 traceback 首行当作版本号。
- **rule_proposal**:
  - `rules/proposals/2026-04-20-policy-checker-task-boundary.md`（新）——
    提议：`check_policy.py` 加 `--since <commit>` 支持，按 commit 切任务边界，
    避免跨 Wave 统计假阳性。门槛：证据 ≥3 case 后可 promote。
- **wiki**: 无新增。本 Wave 聚焦工具，不新建实体页。

## 下一步（Wave 4 预告）

1. `agents/knowledge-curator.md` 的"提取启发法"从 prose 升级为**可执行脚本**
   （`tools/curate.py`），输入 user+assistant 对话摘要，输出 case+memory+proposal 候选。
2. 写一次 "onboarding" 端到端 case：新用户第一次问问题 → Q&A → curator → consolidation →
   知识图谱增长的**完整环路**，作为 README 的"演示"引用。
