# Ascend-Forge 架构设计

> 一个面向**昇腾生态大模型适配 / 部署 / 调优**的自进化 Agent。
> 设计目标：在 Claude Code 中开箱即用，同时可无缝迁移到 openclaw、OpenHands/OpenDevin、Cursor、Cline 等任何支持"文件化 Agent"的平台。

---

## 1. 设计原则

1. **一切皆文件 (Everything-as-File)**：所有"Agent 状态"（记忆、技能、Wiki、案例、规则）都是 Markdown / JSONL，Git 友好、人类可读、跨平台零成本迁移。
2. **平台无关内核 + 适配器 (Core + Adapters)**：内核只定义"目录契约 + 进化循环"；`adapters/` 里放各平台的 bootstrap 与能力映射。
3. **进化是一等公民 (Evolution as First-class)**：不是"跑完任务拍拍屁股走人"，而是**每一次交互都必须沉淀为可检索的知识资产**。进化动作由专门的 `knowledge-curator` subagent 负责，和业务 subagent 解耦。
4. **稀疏优于密集 (Sparse > Dense)**：上下文只加载**当前任务需要的**切片——靠索引而非全文注入，避免"越用越慢越傻"。
5. **可审计、可回滚 (Auditable & Reversible)**：所有自更新都走 proposal → review → active 三段式；规则/Wiki 变更在 Git 历史里。

---

## 2. 分层架构

```
┌────────────────────────────────────────────────────────────────┐
│  Platform Adapters                                             │
│  ─────────────────                                             │
│  adapters/claude-code/   adapters/openclaw/   adapters/…       │
│  • bootstrap 入口        • 能力映射           • 工具桥接        │
│  • CLAUDE.md / agents/   • AGENTS.md          • tool shim       │
└────────────────────────────────────────────────────────────────┘
                              ▲
                              │  读/写同一套目录契约
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Core Agent (平台无关)                                          │
│  ───────────                                                   │
│  • Router / Planner       (路由到 subagent)                    │
│  • Retriever              (INDEX → 切片 → 注入上下文)           │
│  • Evolution Loop         (观察 → 萃取 → 落盘 → 合并)           │
│  • Policy Guard           (进化的安全/速率/冲突策略)            │
└────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Knowledge Substrate  (五种互补的知识载体)                      │
│  ────────────────────                                          │
│  1) memory/    结构化事实/教训/坑/偏好，原子化、强 schema       │
│  2) skills/    可复用 SOP（SKILL.md，带触发条件）               │
│  3) wiki/      Karpathy-style LLM Wiki，主题页 + 双向链接       │
│  4) cases/     案例库（每次任务一份归档，支持 RAG）             │
│  5) rules/     自更新启发式规则，三段式生命周期                 │
└────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Business Subagents  (昇腾域)                                   │
│  ───────────────────                                            │
│  ascend-adapter   / ascend-deployer   / ascend-tuner            │
│  ascend-diagnoser / ascend-benchmarker / ascend-env-doctor      │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. 知识基座：为什么要五种载体？

这是本设计的灵魂。很多 "self-improving agent" 项目只用一种载体（通常是向量库），结果要么**检索噪声大**，要么**只能记事实、记不住流程**。我们按**知识形态**分类存储：

| 载体 | 形态 | 何时写入 | 何时读取 | 失效策略 |
|---|---|---|---|---|
| `memory/facts` | 原子事实（<= 1 句） | 用户确认或可验证的事实 | 每个任务启动时按主题检索 | 带 `verified_at`，过期告警 |
| `memory/lessons` | 复盘短文（3–10 行） | 任务后的 retro | 同主题任务前 | `applies_to` 过滤 |
| `memory/pitfalls` | 坑 + 规避 | 遇到过的报错/陷阱 | 报错签名命中即弹出 | signature hash 精确匹配 |
| `memory/preferences` | 用户偏好 | 用户说"我喜欢/总是/不要" | 全局常驻 | 冲突时以新覆盖旧，需用户确认 |
| `skills/*/SKILL.md` | SOP/剧本 | 一类操作被**重复 ≥ 2 次** | 触发词匹配 | 版本化，跑失败会进 pitfalls |
| `wiki/**.md` | 主题百科页 | 对一个**实体**（模型/算子/错误/硬件）积累结构化认知 | 实体被提及 → 按链接拉取 | Git blame + `last_verified` |
| `cases/*.md` | 案例（问题+过程+结论） | 每次任务结束 | 语义相似度 TopK | TTL / 重要性评分 |
| `rules/ACTIVE.md` | 启发式规则 | Curator 观察到重复模式 | 每次规划前全量加载（短） | proposal → review → active |

### 3.1 Wiki 的实现（Karpathy LLM-Wiki 概念的落地）

Karpathy 那篇 gist 的核心主张：让 LLM 维护一个**自己写给自己看的、高度交叉引用的 wiki**，每个概念一页，更新时去重、链接整个知识网。

我们的落地方案：

- **一页一实体**：每个 GPU 型号 / 软件栈 / 模型 / 算子 / 错误签名 / 场景 playbook 各一页。
- **Frontmatter Schema（必填）**：

  ```yaml
  ---
  id: mindie-2.0            # kebab-case，全局唯一，也是文件名
  title: MindIE 推理引擎
  kind: software             # hardware|software|model|operator|error|playbook
  aliases: [MindIE, mindie]
  tags: [inference, huawei, ascend]
  related: [cann, mindformers, vllm-ascend]   # 双向链接目标
  status: stable             # draft|stable|deprecated
  last_verified: 2026-04-20
  sources:
    - https://www.hiascend.com/document/...
  ---
  ```

- **页面模板（按 kind 分化）**：
  - `software`：概览 / 版本矩阵 / 安装 / 常见坑 / 相关算子 / 相关模型
  - `model`：架构 / 昇腾适配状态 / 替换过的算子 / 精度基线 / 性能基线 / 已知坑
  - `operator`：原始定义 / 昇腾替换方案 / 精度差异 / 性能 / 相关模型
  - `error`：签名（正则/关键词）/ 触发条件 / 根因 / 修复 / 引用 case
  - `playbook`：场景 → 步骤 → 调用哪些 skill → 验证标准

- **双向链接**：每页末尾有 `## Backlinks`（由 `tools/wiki_link_check.py` 自动维护）。
- **搜索**：`wiki/INDEX.md` 是手写+自动合并的索引；另有 `wiki/INDEX.jsonl`（机器可读）。
- **更新契约**：新知识进来时——
  1. 先找**最窄**匹配的实体页（按 id + aliases + 语义）。
  2. 命中 → 追加到对应小节（不覆盖，追加带日期）。
  3. 未命中 → 新建一页；若该实体是"大类下某子型"，必须在父页加链接。
  4. 每次变更必须留下一行 changelog。

> **与 memory/ 的分工**：memory 是"原子 + 横切"（比如"用户偏好 W8A8 量化"），wiki 是"实体 + 纵深"（比如"Qwen2-72B 在 910B 上的完整档案"）。同一条信息可能在两处出现——这是**刻意的冗余**，因为检索路径不同。

---

## 4. 进化循环（Evolution Loop）

```
        ┌─────────────┐
        │  1 OBSERVE  │  把对话/工具调用/报错打成 trace
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  2 EXTRACT  │  curator subagent 抽取候选知识
        │             │  （fact? lesson? pitfall? skill?
        │             │   wiki-update? rule-proposal?）
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  3 CLASSIFY │  选择载体 + 目标文件（查重）
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  4 LAND     │  写入（或生成 proposal，等 review）
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  5 CONSOLID │  周期性：merge 重复、退役失效、
        │             │  重建索引、更新 backlinks
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  6 RETRIEVE │  下次任务：用新知识（回到 1）
        └─────────────┘
```

### 4.1 触发时机

| 时机 | 动作 | 执行者 |
|---|---|---|
| **每个任务结束**（同步） | 生成 `cases/<date>-<slug>.md`，萃取 ≤ 3 条候选知识 | `knowledge-curator` subagent |
| **用户说"记住…/以后都…"**（同步） | 直接写 `memory/preferences/` + rule proposal | 主 agent |
| **重复模式 ≥ 2 次** | 提案升级：`case → skill` 或 `fact → rule` | curator |
| **每日/每周**（异步） | 运行 `tools/evolve.py`：consolidation、去重、索引重建、链接修复 | 调度任务 |
| **人工触发** `/consolidate` | 同上 | 用户 |

### 4.2 安全护栏（Policy Guard）

- **白名单路径**：Agent 只能写 `memory/ skills/ wiki/ cases/ rules/proposals/`，**禁止**直写 `rules/ACTIVE.md`。
- **写入必须带源头**：每次落盘附 `source: case/<id>` 或 `source: user-confirmed`。
- **冲突检测**：新事实与已有事实矛盾时，走 proposal 让用户裁决，不静默覆盖。
- **速率限制**：单次任务最多产出 3 条新 memory / 1 条新 skill / 1 条 rule proposal，避免"噪声爆炸"。
- **Prompt 规则自更新**只允许追加到 `rules/proposals/`，必须人工或 `/rules promote` 才进 ACTIVE。
- **所有变更走 Git**：强烈建议用户把 ascend-forge 本身纳入 Git，每次 consolidation 一次 commit。

---

## 5. 运行时数据流

以一次"Qwen2-72B 在 910B 部署 OOM"任务为例：

```
用户: "Qwen2-72B 上 910B×8 起 MindIE 报 ACL_ERROR 500002，OOM"
  │
  ▼
[Router] 识别意图 = 诊断+部署 → 选 ascend-diagnoser + ascend-deployer
  │
  ▼
[Retriever] 并发拉取：
  • memory/pitfalls/*qwen2* + *oom*           (精确签名)
  • wiki/models/qwen2-72b.md                  (实体页)
  • wiki/errors/acl-500002.md                 (错误签名页)
  • skills/mindie-deployment/SKILL.md
  • cases/ 中语义 TopK=3
  │
  ▼
[ascend-diagnoser] 给出假设 → [ascend-deployer] 尝试修复
  │
  ▼
[knowledge-curator] 任务结束，产出：
  • cases/2026-04-20-qwen2-72b-oom.md         (完整归档)
  • memory/pitfalls/acl-500002-qwen2.md       (新坑)
  • wiki/models/qwen2-72b.md 追加一节 "已知 OOM 场景"
  • wiki/errors/acl-500002.md last_verified 刷新
  • rules/proposals/2026-04-20-check-kvcache-before-oom.md
```

---

## 6. 昇腾业务 Subagent 初始阵容

| Subagent | 职责 | 主要 skill | 主要 wiki 分区 |
|---|---|---|---|
| `ascend-adapter` | PyTorch→torch_npu / MindSpore 迁移、算子替换、精度对齐 | `model-adaptation`, `operator-replacement`, `precision-alignment` | `wiki/models`, `wiki/operators` |
| `ascend-deployer` | MindIE / MindFormers / vLLM-Ascend 服务化 | `mindie-deployment`, `vllm-ascend-serving` | `wiki/software`, `wiki/playbooks` |
| `ascend-tuner` | 显存 / 吞吐 / 时延调优、量化 | `memory-optimization`, `msprof-profiling` | `wiki/models`, `wiki/operators` |
| `ascend-diagnoser` | 报错定位、精度验证、瓶颈分析 | `msprof-profiling`, `precision-alignment` | `wiki/errors` |
| `ascend-benchmarker` | 基准测试、性能基线、回归对比 | `benchmark-baseline` | `wiki/models`（perf 小节） |
| `ascend-env-doctor` | CANN / 驱动 / 固件、910B / 310P 硬件检查 | （TBD） | `wiki/hardware`, `wiki/software` |
| `knowledge-curator` | **进化循环执行者**（元 agent） | `knowledge-capture` | 全域 |

---

## 7. 跨平台迁移策略

| 平台 | 入口 | Subagent 形式 | 其他适配 |
|---|---|---|---|
| **Claude Code** | `CLAUDE.md` (repo 根) | `agents/*.md` (原生支持) | `.claude/settings.json`（可选） |
| **openclaw / Cline / Cursor** | `AGENTS.md` (业界正在形成的"中立规范") | 主 agent 加载 `AGENTS.md` + `agents/` 目录，其视为"角色说明书" | 工具调用用平台原生 Bash/Edit |
| **OpenHands / OpenDevin** | `.openhands/` 配置指向仓库根 | 同上，视为 persona prompts | MCP 工具桥 |
| **裸 LLM API / LangGraph** | `adapters/<你的>/bootstrap.py` 读 `AGENTS.md` + `agents/` 作为 system prompt | 代码层显式路由 | 自行实现 retriever |

**核心契约**：任何平台只需满足以下 3 条，就能运行 ascend-forge：

1. 能执行 Bash（或等价的 shell 工具）。
2. 能读写仓库内任意文件。
3. 支持"多轮对话 + 子任务 / 子 agent 调用"（或至少能 prompt 链式调用）。

> 详见 [`docs/PORTING.md`](PORTING.md)。

---

## 8. 非目标 (Non-Goals)

- **不做**在线 fine-tune / LoRA 训练闭环——这是"Agent 行为进化"，不是"模型参数进化"。
- **不做**向量数据库强耦合——可插拔（默认 grep+BM25 够用，百级以内 case 完全不需要向量）。
- **不做**自动执行破坏性命令（如 `rm -rf`, `dd`, 驱动覆盖），这类需要二次确认。
- **不假设**一定有 NPU 机器在手——agent 本身可以纯文本工作，只在 `tools/` 里对接真机脚本。

---

## 9. 成熟度路线图

- **v0.1 骨架（现在）**：目录契约 + 文档 + 空模板。用户可以用 Claude Code 跑，但知识库是空的。
- **v0.2 种子**：把 CANN / MindIE / MindSpore / vLLM-Ascend / 910B / 310P 这 6 个核心 wiki 页写到"可用"水平。
- **v0.3 闭环**：`knowledge-curator` 能端到端跑通"任务 → case → wiki 更新 → rule 提案"。
- **v0.4 多模型预设**：预置 Qwen / DeepSeek / Llama / InternLM 的 wiki stub。
- **v0.5 跨平台**：验证 openclaw/OpenHands 下的同等行为。
- **v1.0**：`tools/evolve.py` 成熟、冲突裁决机制、长期稳定。

---

## 10. 参考

- Karpathy, *"LLM Wiki"* gist — 本项目 wiki 基座的灵感来源。
- Anthropic Claude Code `agents/` & `skills/` 规范。
- OpenAI / Cursor / Cline 社区正在收敛的 `AGENTS.md` 约定。
- 昇腾官方文档：CANN / MindIE / MindFormers / MindSpore。
