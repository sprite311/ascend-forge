# Ascend-Forge

> **一个面向昇腾生态大模型适配 / 部署 / 调优的自进化 Agent**
> 为 Claude Code 而生，平台无关设计，可无缝迁移到 openclaw / OpenHands / Cursor / Cline / 裸 API。

---

## 这是什么

Ascend-Forge 不是一段代码，而是**一套会自己长大的知识 + Agent 目录结构**。
你在 Claude Code 里和它对话、让它干活——它会把每一次交互沉淀成：

- 📌 **memory/**：原子事实、教训、坑、你的偏好
- 📖 **wiki/**：每个模型 / 算子 / 错误 / 硬件 / 软件的主题百科页（Karpathy 风格）
- 🛠 **skills/**：被重复过的操作固化成可触发的 SOP
- 📚 **cases/**：每次任务的完整归档，供将来 RAG
- 📜 **rules/**：自更新的启发式规则（三段式生命周期，可审计）

下一次遇到同类问题，这些知识被**自动检索并注入**，让 agent 越用越懂昇腾、越懂你。

## 快速开始

### Claude Code

```bash
cd ascend-forge
# Claude Code 会自动读 CLAUDE.md
```

然后直接提问：

```
> Qwen2-72B 想在 910B×8 上起 MindIE 服务，OOM 了，帮我看看
```

Agent 会：
1. 读 `rules/ACTIVE.md`（短规则全量加载）
2. 按关键词命中 `wiki/models/qwen2-72b.md`、`wiki/errors/`、`skills/mindie-deployment/`、`cases/` TopK
3. 路由到 `@ascend-diagnoser` + `@ascend-deployer`
4. 任务结束由 `@knowledge-curator` 写入 case + 更新 wiki + 可能提 rule 提案

### 其他平台

见 [`docs/PORTING.md`](docs/PORTING.md)。入口换成 `AGENTS.md`，其他目录原样复用。

## 目录地图

```
ascend-forge/
├── CLAUDE.md                ← Claude Code 入口
├── AGENTS.md                ← 平台无关入口（openclaw/Cursor/Cline/OpenHands）
├── .agent/                  ← 内核配置
│   ├── config.yaml
│   ├── system_prompt.md
│   └── evolution_policy.md
├── agents/                  ← Subagent 定义（平台无关）
│   ├── knowledge-curator.md ★ 自进化执行者
│   ├── ascend-adapter.md
│   ├── ascend-deployer.md
│   ├── ascend-tuner.md
│   ├── ascend-diagnoser.md
│   ├── ascend-benchmarker.md
│   └── ascend-env-doctor.md
├── skills/                  ← 可复用 SOP（带 trigger）
├── memory/                  ← facts / lessons / pitfalls / preferences
├── wiki/                    ← Karpathy-style 主题百科（hardware/software/models/operators/errors/playbooks）
├── cases/                   ← 每次任务的归档
├── rules/                   ← ACTIVE + proposals + archive
├── tools/                   ← evolve.py / wiki_link_check.py / rag_index.py
├── adapters/                ← claude-code / openclaw 等平台胶水
└── docs/
    ├── ARCHITECTURE.md      ★ 核心设计
    ├── EVOLUTION.md         ★ 进化循环详细规范
    ├── KNOWLEDGE-MODEL.md   ★ 五种知识载体 schema
    └── PORTING.md           ★ 跨平台迁移指南
```

## 阅读顺序

第一次接触：**[ARCHITECTURE](docs/ARCHITECTURE.md) → [EVOLUTION](docs/EVOLUTION.md) → [KNOWLEDGE-MODEL](docs/KNOWLEDGE-MODEL.md) → [PORTING](docs/PORTING.md)**。

## 当前版本

`v0.1` — 骨架 + 文档 + 空模板。知识库是空的，用起来会自然变满。
路线图见 [`docs/ARCHITECTURE.md §9`](docs/ARCHITECTURE.md#9-成熟度路线图)。

## 许可

TBD
