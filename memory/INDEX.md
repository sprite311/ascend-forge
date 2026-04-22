# Memory Index

> 由 `knowledge-curator` 维护。每次 consolidation 重建。
> 只放索引项（id、tags、一句话摘要、source）；详细内容在对应 md 文件。
> **最近一次 consolidate**: 2026-04-22 (Wave 9 后)

---

## Facts (`facts/`)
<!-- id | tags | summary | source -->
- [fact-ascend-three-piece-matrix](facts/fact-ascend-three-piece-matrix.md) — `[version, torch, torch-npu, cann, compat-matrix]` — PyTorch×torch_npu×CANN×Python 强耦合，错一档即 segfault（**user-confirmed 简版**） — src: `skill/ascend-troubleshoot/references/version_matrix.md`
- [fact-torch-npu-version-matrix-25q1](facts/fact-torch-npu-version-matrix-25q1.md) — `[version, cann, driver, python, compat-matrix]` — CANN×driver/firmware×torch×torch_npu×Python 详细组合表（2025Q1 cutoff 口径，含 OS 推荐） — src: `training-knowledge-cutoff-2025-05`
- [fact-ascend-hardware-specs](facts/fact-ascend-hardware-specs.md) — `[hardware, 910b, 910c, 310p, 310b, atlas, specs]` — 910B/B2/B3/C + 310P/B 显存/算力/TDP 速查 + HCCS/RoCE 互联 + npu-smi 命令 — src: `training-knowledge-cutoff-2025-05`

## Lessons (`lessons/`)
- [lesson-seed-page-must-link-errors](lessons/lesson-seed-page-must-link-errors.md) — `[wiki, content-design, cross-link, curator]` — 软件/硬件种子页必须反链 `wiki/errors/` 高频条目 — src: `case/2026-04-20-troubleshoot-migration-wave1`
- [lesson-yaml-parser-inline-comment-and-blocklist](lessons/lesson-yaml-parser-inline-comment-and-blocklist.md) — `[tooling, parser, yaml, frontmatter]` — 手写 YAML 子集 parser 必须覆盖 inline-comment + block-list 两种形态 — src: `case/2026-04-20-wave3-tooling`
- [lesson-architecture-critique](lessons/lesson-architecture-critique.md) — `[architecture, refactor, self-reflection, tech-debt]` — Wave 5/8 架构痛点清单（DRY、状态机、分类器、规则边界、L4 gap、time-to-x KPI…） — src: `case/2026-04-20-wave5-close + 2026-04-22-wave8`

## Pitfalls (`pitfalls/`)

### 昇腾技术坑（runtime / framework / operator）
- [pitfall-sdpa-not-implemented-on-npu](pitfalls/pitfall-sdpa-not-implemented-on-npu.md) — `[attention, sdpa, hf-transformers, op-missing]` — HF 模型落 NPU 报 `aten::_scaled_dot_product_flash_attention`；90% 迁移首坑；修法：`attn_implementation="eager"` 或 patch `npu_fusion_attention` — src: `training-knowledge-cutoff-2025-05`
- [pitfall-rope-half-convention-mismatch](pitfalls/pitfall-rope-half-convention-mismatch.md) — `[rope, rotary, precision, silent-bug]` — Neox 前后半对 vs GPT-NeoX 相邻对——`loss 正常但生成乱码`的隐蔽 bug；首日做逐层 diff 才防得住 — src: `training-knowledge-cutoff-2025-05`
- [pitfall-hccl-multi-node-timeout](pitfalls/pitfall-hccl-multi-node-timeout.md) — `[hccl, multi-node, ranktable, rocev2]` — 多机 HCCL 起不来或第 N 步超时；checklist：hccn_tool → ranktable → env vars → 心跳日志 — src: `training-knowledge-cutoff-2025-05`
- [pitfall-dtype-mixing-bf16-fp16](pitfalls/pitfall-dtype-mixing-bf16-fp16.md) — `[dtype, bf16, fp16, mixed-precision, silent-bug]` — BF16/FP16 混用精度漂移或 dtype mismatch；910B/C 首选 BF16，别混 — src: `training-knowledge-cutoff-2025-05`
- [pitfall-block-size-alignment](pitfalls/pitfall-block-size-alignment.md) — `[inference, vllm, block-size, memory, alignment]` — vLLM/SGLang 在昇腾上 block-size 必设 64/128，默认 16 直接崩 — src: `skill/ascend-troubleshoot/references/knowledge_base.md#INF-002`

### Agent 自反 / 工具坑（元层）
- [wiki-seed-page-tbd-blind-answer](pitfalls/wiki-seed-page-tbd-blind-answer.md) — `[bootstrap, wiki, confidence, seed-page]` — 种子页 TBD 段易被当权威事实；遇 draft 必须降权 — src: `case/2026-04-20-porting-selfcheck`
- [pitfall-traceback-as-version](pitfalls/pitfall-traceback-as-version.md) — `[tooling, subprocess, version-detection]` — `python -c "import X;print(X.__version__)"` 探测时必须过滤 Traceback/ImportError 失败标记 — src: `case/2026-04-20-wave3-tooling`
- [pitfall-tool-name-vs-intent-verb](pitfalls/pitfall-tool-name-vs-intent-verb.md) — `[routing, classifier, bench, intent-detection]` — 关键词 bag 路由无法区分"提到 X"和"用 X 做 Y"；bench 81.2% 上限根因 — src: `case/2026-04-21-wave6`
- [pitfall-cross-session-state-amnesia](pitfalls/pitfall-cross-session-state-amnesia.md) — `[self-reflection, session, ground-truth, ls-before-claim]` — compaction + 副 session 并发致主 session 事实错误；量化断言前必 `ls` verify — src: `case/2026-04-22-wave8`

## Preferences (`preferences/`)
_暂无条目。_

---

## 维护约定

- 新增条目时在对应小节**追加一行**，模板如下（`KIND` 为 `facts` / `lessons` / `pitfalls` / `preferences` 之一；`ID` 为条目的 kebab-id）：

  ```
  - [ID](KIND/ID.md) — `[tag1, tag2]` — 一句话摘要 — src: `case/…` 或 `user-confirmed` 或 `training-knowledge-cutoff-<yyyy-mm>`
  ```

- 过期（超过 `ttl_days` 未 reverify）条目前面加 `⚠️`。
- 被取代的条目移到 [`archive/`](#archive) 小节（独立 `archive/` 目录可选）。
- 单文件行数 > 300 建议拆分主题子索引。
- **provenance 双轨**：`user-confirmed`（或 `case/<id>`）= 高置信；`training-knowledge-cutoff-<yyyy-mm>` = 训练期知识，回答时按 R033 降权。

## 重叠 / 关联关系（cross-ref）

- `fact-ascend-three-piece-matrix` ↔ `fact-torch-npu-version-matrix-25q1`：前者是用户确认的简版口诀，后者是训练期的详细矩阵（含 driver/firmware 行、OS 推荐）。**保留两者**——真机回执升升 stable 前，新条目降权使用。
- `pitfall-sdpa-not-implemented-on-npu` ↔ `pitfall-rope-half-convention-mismatch`：同为 HF 迁移首日坑，但一显一隐（SDPA 显式报错 / RoPE 静默乱码），在迁移 playbook `wiki/playbooks/hf-to-npu-7-step.md` Step 3/4 成对出现。
- `pitfall-dtype-mixing-bf16-fp16` ↔ `pitfall-rope-half-convention-mismatch`：都属于"loss 对但生成错"的 silent-bug 家族，迁移首日逐层 diff 两类同时排。

## Archive
_无_
