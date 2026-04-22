---
id: lesson-architecture-critique-wave5
date: 2026-04-21
tags: [architecture, refactor, self-reflection, wave5, wave8, tech-debt, frontline-alignment]
status: active
source: case/2026-04-20-wave5-close
ttl_days: 180
verified_at: 2026-04-22
---

# Wave 5 回看：Ascend-Forge 骨架的 10 个架构痛点 + 已修 / 待修
# Wave 8 补：对照小组讨论（"一个大脑 · 四层记忆 · 5天→0-1天"目标）的新增 3 条

在 Wave 1–5 把骨架搭到能端到端跑之后，刻意停下来反思：**这个 Agent 目前的工程设计真的是最优吗？**
下面这 10 条是在 Wave 5 refactor 中识别出的真实痛点（不是空想），按"已修 ✅ / 修了一半 🟡 / 还没修 ⚫"分档，后续每次 consolidation 可以回来翻。

---

## ✅ 1. `parse_frontmatter` 被复制了 5 次 —— 已抽到 `tools/_common.py`

**症状**：`evolve.py / wiki_link_check.py / rag_index.py / promote.py` 各有一份同名同实现的 `parse_fm`，`check_policy.py` 也有 `FRONTMATTER_RE`。Wave 3 发现的 2 个 YAML parser bug（inline-comment leak、multi-line block list 丢失）**各修了 3 次**，才让 3 份 copy 一致。

**根因**：骨架阶段为了"工具自包含、互不依赖"，每个 tool 都内联了解析器。代价是发散风险——任何一处修 bug 都要同步扫其他 copy。

**已修**：`tools/_common.py` 导出 `ROOT / FRONTMATTER_RE / parse_frontmatter / strip_frontmatter / banner / iter_cases`。5 个 tool 改成 `from _common import ...`，净减 ~160 行重复代码。

**教训**：**"工具自包含"是启动期的便利，不是长期结构**；只要有第 3 份 copy 出现，就该立刻抽公共。阈值 = 3。

---

## ✅ 2. `tools/evolve.py` Step 7 把**已 promoted** 的 proposal 仍标为 🟢 ready —— 已修

**症状**：R033 晋升后，再跑 `evolve.py`，Step 7 输出仍是 `🟢 seed-critical-wiki-before-first-use ... evidence=3`。用户看了会以为"还没 promote"。

**根因**：Step 7 只比较 `evidence ≥ 3`，没检查 `status`。`promote_ready` 应该是 `pending AND evidence ≥ 3`，而不是 `evidence ≥ 3` 一个条件。

**已修**：按 status 分四档 `✅ promoted / ⚫ rejected|superseded / 🟢 ready / 🟡 pending`；`proposals_ready` 计数也不再把已 promoted 的算进去。

**教训**：**状态机的终止态要显式判**，别指望"自然退出"。

---

## ✅ 3. `promote.py` 把新规则插到 `---` 分隔线和 `## 说明` 之间 —— 已修

**症状**：第一次跑 `promote.py --apply` 时，R033 被写到了 ACTIVE.md 最末、`---` 分隔线之后，视觉上"游离"于所有 section 外。手动把它挪回 `## Evolution` 段。

**根因**：原来的 section-end 检测只认 `\n##\s`，不认 `\n---\s*\n`。当目标 section 是文件最后一个 section（`## Evolution`）时，section 末尾 = 文件末尾 = `---` 分隔线，代码直接追加到了文件末尾。

**已修**：`nxt = re.search(r"\n(##\s|---\s*\n)", ...)` 同时识别两种 section 终止符；另外给"section 完全不存在"的情况加了 `divider` 前插逻辑。

**教训**：**文档结构的边界要同时考虑"下一 section 起点"和"全局分隔符"**，不能只认其一。

---

## 🟡 4. `tools/bench.py` 的分类器是**关键词加权**，不是真的意图理解 —— 部分修，长期重构

**症状**：首跑 14/15，Q12 "推理服务 OOM" 被路由到 deployer（6 分）而非 diagnoser（5 分）。去掉裸 `服务` 关键词后过 15/15。但这不是"问题解决了"，而是"测试用例躲开了 bug"。

**根因**：按关键词+权重的 bag-of-words 太脆弱，任何一个多义词（`服务` / `性能` / `内存`）都可能同时命中多个 subagent。真实用户问法比 15 条 golden 更花。

**已修（部分）**：调权 + 去噪关键词。

**还没修**：应该引一个"轻量语义分类器"——最小实现是把 15 条 golden 当 few-shot，用 embedding-NN 或者让主 agent 自己做 LLM-based routing。但这会引入依赖（onnxruntime / 或 API 调用），和 Ascend-Forge 的"纯文件、纯 stdlib"原则冲突，需要权衡。

**教训**：**分类器的"训练集"不能是"让测试通过的关键词集"**，这是在逆向给测试打补丁。健康做法：先写 30+ 问题（而不是 15），然后再调分类器；15 条太小，调参会过拟合。

---

## 🟡 5. R031 限额（3 memory / 1 rule / 1 case …）按"write 块"算，但骨架期批量写 —— 语义错位

**症状**：跑 `check_policy.py --from-git`，每次 Wave 结束都报 20+ 违规。大多数是"这次 commit 写了 4 个 memory 文件"之类。实际上这些是**骨架批量生成**而不是"某次真实用户任务"。

**根因**：规则 R031 的"单任务"边界定义是**一次用户交互**，但 `check_policy.py` 用的是 `git diff HEAD`，把"一次 commit 内所有变更"都当一次任务。边界不匹配。

**已提 proposal**：`rules/proposals/2026-04-20-policy-checker-task-boundary.md` —— 给 `check_policy.py` 加 `--since <commit>` 或 `--task-start <timestamp>`，区分"bootstrap commit"和"真实任务"。当前 evidence=1（只有 Wave 3 一次），还没到晋升门槛。

**教训**：**规则文本必须显式定义"单位时间窗口"**，否则任何自动化检查都会把不同粒度的变更一锅炖。

---

## ⚫ 6. `tools/curate.py` 的名字和"真实 curator 子代理"语义重叠 —— 还没改

**症状**：`agents/knowledge-curator.md` 是让**子代理**做沉淀的 markdown 提示；`tools/curate.py` 是用**正则启发式**扫文本提 candidate 的 Python 脚本。两者都叫 "curator"，用户/文档来回引用时容易混。

**建议**：`tools/curate.py` → `tools/extract_candidates.py`（职责更精确），把 "curator" 这个词留给 Agent 端。暂未改是因为会动几个 wiki / case / CLAUDE.md 里的引用，纯文本换词本身就是噪音 commit，想等下次有其它 tools 改动时顺带做。

**教训**：**两层（Agent 层 + 工具层）共用一个词时要警惕**。

---

## ⚫ 7. `tools/evolve.py` 是 8 步线性 orchestrator，没有"只跑 step 3" 的选项 —— 还没改

**症状**：debug 某一步（比如"wiki 链接校验为何没捕到 X"）需要跑全部 8 步 ~10s，翻很多无关输出。

**建议**：加 `--steps 3,5` 选项；现在是全量跑。不紧急——一次 10s 并不痛。

**教训**：**骨架期不要过早做"精细分步"，但要在注释里标好"将来要拆"**，免得半年后有人读代码以为 linear-only 是本意。

---

## ⚫ 8. Wiki `status: draft` 的升级通路不闭合 —— 规则有，工具没 —— 待补

**症状**：R033 要求命中 `draft` 页时降权回答；但"真机验证后 draft → stable"这一步是人工的：curator 要读 case 判断"追加回执够不够硬核"。没有自动化。

**建议**：`tools/wiki_link_check.py` 加一个 "draft stability" 扫描：若某 wiki 页的"追加小节" ≥ 2 条且都带 `source: user-confirmed | case/...`，提示建议升 stable。当前没做是因为真正涉及事实性数据的 wiki 页还只有 qwen3 / flash-attention 等 4–5 个，手工翻得过来。

**教训**：**每条规则都应该问一遍"生效后怎么退出生效窗口？"**——R033 回答了"为何要降权"，但没回答"何时不再需要降权"。

---

## ⚫ 9. 沙箱无法 `unlink`，`promote.py` 只能 fallback 到改 status —— 物理限制，写进设计

**症状**：`Path.unlink()` 和 bash `rm` 都 PermissionError。promote 的原计划（删除原 proposal）不可能实现。

**已缓解**：fallback 把 proposal frontmatter 改成 `status: promoted` + `promoted_at / promoted_to / archive_ref`，让 Step 7 能识别为"已 promote"，同时留存历史。

**教训**：**"删文件"是隐藏的昂贵操作**，好的持久化系统都是 append-only + tombstone；我们这里正好被沙箱逼到了正确方向。

---

## ⚫ 10. `adapters/` 下只有 `README.md`，没有**真的可运行的**同步脚本 —— 未实现

**症状**：`adapters/cursor/README.md` / `adapters/cline/README.md` 写了"怎么把规则映射过去"，但实际上用户要自己 copy-paste。我们没有 `tools/adapter_sync.py --target=cursor` 这种命令。

**建议**：一期实现 `cursor` 和 `openclaw` 两个——这两个最接近"纯文件"形态，最容易做单向同步（Ascend-Forge → Cursor/.cursor/rules/*.mdc）。Cline 涉及 role prompt 切换，复杂度高，留后面。

**教训**：**文档里的"怎么做"和代码里的"真的能做"不是一回事**。骨架期写文档先于写代码是 OK 的，但要在 README 顶注明 `status: planned`。

---

## 总体反思

这 10 条里，**4 条是 DRY/边界错位类问题**（#1 #2 #3 #5），**2 条是语义-工具命名漂移**（#4 #6），**3 条是"规则存在但自动化不闭环"**（#8 #10 还有 #7 的 orchestrator），**1 条是物理限制顺手入设计**（#9）。

共性：骨架阶段写得快是对的，但**每完成一个 Wave 就应该 pause 做一次 retro**——今天的 Wave 5 refactor 让我们真的产出了 5 个文件的 diff + 1 条 lesson + 明确的后续清单。如果不 pause，这些 tech debt 会一直隐着。

---

---

# Wave 8 补丁：对照小组讨论的"一个大脑、四层记忆、5 天→0-1 天"目标

小组目标原文（Wave 8 收到）：
> 一个大脑，四层记忆，答得准 · 通过任务执行总结沉淀复盘案例，形成可复制的方案/脚本 · 5 天→0-1 天 ·
> 场景 1：平台生成案例 → 客户现场交付；场景 2：现场交付 → 牵引回平台复现。

对照当前架构，**原 10 条痛点都是"工程卫生"问题**，但从 Wave 5/6/7 到现在我们只产出**知识原子**（lesson/pitfall/fact）和**索引**——**没产出"可复制的脚本"**。这是一个**方向性差距**，列为 #11/#12/#13。

---

## 🟡 11. **程序性记忆层（skills/）是 SOP 文档，不是可跑脚本** —— 方向性差距（已修正）

> **2026-04-22 附：本条原文说"skills/ 基本为空"，是事实错误**；见 `pitfall-cross-session-state-amnesia`。
> 修正后的版本如下。

**症状**：
- `memory/` 5 条（2026-04-22 计；增了 1 条 pitfall）
- `wiki/` 24 页（多数 draft）
- `cases/` 8 条（Wave 1-8 收尾）
- **`skills/`**：**12 个** skill，每个都有 SKILL.md（40-128 行），但**绝大多数是步骤描述而非可跑脚本**——
  - 11 个 bootstrap skill（model-adaptation / mindie-deployment / msprof-profiling / ...）写的是"先 pip install X，再改 config Y，验证 Z" 这种 SOP；
  - 唯一 "新" skill `wiki-consolidate-draft-to-stable` 包装的是 `tools/wiki_stability.py`——**这一个**是 doc→tool 的闭环，其他 11 个没有。

**意味着什么**：小组说"5 天 → 0-1 天"的加速要靠**脚本**（bash/python/Dockerfile/env.yaml）——但我们的架构里"脚本"这一层是**空的**。我们在第一层（知识原子）做得很好，在第四层（可执行程序）一片空白。

**根因**：
1. `@knowledge-curator` 的"每任务最多 1 skill"是上限，不是下限——可以 0，但实际就都是 0。
2. 没有"case → skill 模板化"工具：每次沉淀都要从零写 SKILL.md，成本高，自然懒。
3. 沙箱无法跑昇腾命令，"脚本"在 Ascend-Forge 内跑不起来，反馈回路缺失（我写的脚本无人立刻验证）。

**紧急度**：🟡 高，但从"🔴 最高"降档——我们有文档层**可工作**的 SOP，只是缺"自动化脚本"那一跳。这是从"SOP 手册"到"**一键作战**"的分水岭，但不是从零起步。

**建议修法**：
- **R034 proposal**：`outcome=resolved` 的 case 必须在 Curator Log 里给出 **skill_status**：`created: skills/xxx` 或 `skipped_because: <具体原因>`。不能放空。
- `tools/case_to_skill.py`：读一个 case，扫"做了什么"段，scaffold 出 `skills/<slug>/SKILL.md` + `skills/<slug>/run.sh`（带 TODO 占位）。让 curator 去填而不是从零写。
- 第一批候选 skill（对照现有 cases）：
  - `skills/ascend-bootstrap-env/`（CANN / 驱动自检 + 版本矩阵校验）
  - `skills/ascend-hf-to-npu-migration/`（HF 模型→910B 迁移 7 步走）
  - `skills/bench-golden-regression/`（跑 bench.py，diff 上次结果，block merge）
  - `skills/wiki-consolidate-draft-to-stable/`（已有 `wiki_stability.py` 工具，缺 playbook 壳子）

---

## ⚫ 12. Case 没有"可复现清单"（reproducibility manifest） —— 方向性差距

**症状**：当前 `cases/*.md` 是**自然语言复盘**，没结构化环境快照（CANN / driver / torch_npu / model id / NPU SoC / batch-size / 输入 shape）。
场景 2 ("客户现场 → 平台复现") 的入口被堵死：**不知道复现什么环境**。

**建议**：case frontmatter 扩 `repro:` 段：
```yaml
repro:
  hardware: [910B]
  cann: "8.0.RC2"
  torch_npu: "2.4.0.post1"
  model: "Qwen2-7B"
  prompt_shape: [1, 2048]
  reproduced_on_sites: 0     # 场景 2 每次复现 +1，作为 skill 成熟度信号
```

没有这段，就没法说某 case "在 N 个局点复现过"——而这正是小组要的**信心度量**。

---

## ⚫ 13. 没有时间度量（time-to-x） —— 验收标准无法自证

**症状**：小组验收标准是"迁移 5 天 → 0-1 天"——**我们没有任何时间字段**。bench.py 测路由准度，不测工时。

**建议**：case frontmatter 扩：
```yaml
time_spent_hours: 3          # 本次实际耗时
baseline_hours: 40           # 没有 Ascend-Forge 会用多久（凭印象）
skills_used: [xxx, yyy]      # 用了哪些 skill 加速
skills_produced: [zzz]       # 本次沉淀出哪些 skill
```

每次 `tools/evolve.py` 聚合成 `docs/EVOLUTION-STATS.md` 加一行：`平均提速倍数 = Σbaseline / Σactual`。这样验收标准有数。

---

## 对照"四层记忆"看现状

| 团队定义的层 | 映射到当前 | 当前状态 |
|---|---|---|
| L1 工作记忆（当前任务上下文） | 每次会话的 session | ✅ 天然具备 |
| L2 情景记忆（发生过的事） | `cases/` + `memory/pitfalls,lessons` | ✅ 良好（7 cases, 4 memory atoms） |
| L3 语义记忆（事实/参考） | `wiki/` + `memory/facts` | 🟡 24 页但多 draft |
| L4 程序记忆（可执行方案） | `skills/` + `tools/` | ❌ **skills 为空；这是主缺口** |

"一个大脑"的结构是对的，但**L4 是空的**——我们是一个**只会回忆、不会动手**的大脑。

---

## 后续行动清单（不 auto-fire，人看了决定）

- [ ] Wave 6 或下次 tools/ 大改动时，给 `tools/curate.py` 改名 → `tools/extract_candidates.py`，同步更新 `agents/knowledge-curator.md` 的引用。
- [x] Wave 6：把 bench 题库从 15 扩到 30+，再评估要不要换分类器。（完成，81.2% 作为关键词 bag 上限，pitfall 已沉淀）
- [ ] Wave 6：实现 `tools/adapter_sync.py --target=cursor|openclaw`（cline 延后）。
- [ ] 持续：新 proposal 达到 evidence ≥ 3 时用 `tools/promote.py --id <id> --apply`，替代 `/rules promote` 手动流程。
- [ ] 持续：`rules/proposals/2026-04-20-policy-checker-task-boundary.md` 凑第 2/3 条 evidence（下次真的有"单任务超限"时记 case）。
- [ ] **Wave 9（最高优）：把 L4 程序层补起来——`tools/case_to_skill.py` + 第一批 4 个 skill 脚手架。**
- [ ] **Wave 9：R034 proposal——"outcome=resolved 的 case 必须填 skill_status（created 或 skipped_because）"。**
- [ ] **Wave 9：case frontmatter schema 扩 `repro:` + `time_spent_hours` / `baseline_hours`。先改一个样板 case，再决定是否强制 lint。**
