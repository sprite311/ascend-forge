# Memory Index

> 由 `knowledge-curator` 维护。每次 consolidation 重建。
> 只放索引项（id、tags、一句话摘要、source）；详细内容在对应 md 文件。

---

## Facts (`facts/`)
<!-- id | tags | summary | source -->
- [fact-ascend-three-piece-matrix](facts/fact-ascend-three-piece-matrix.md) — `[version, torch, torch-npu, cann, compat-matrix]` — PyTorch×torch_npu×CANN×Python 强耦合，错一档即 segfault — src: `skill/ascend-troubleshoot/references/version_matrix.md`

## Lessons (`lessons/`)
- [lesson-seed-page-must-link-errors](lessons/lesson-seed-page-must-link-errors.md) — `[wiki, content-design, cross-link, curator]` — 软件/硬件种子页必须反链 `wiki/errors/` 高频条目 — src: `case/2026-04-20-troubleshoot-migration-wave1`
- [lesson-yaml-parser-inline-comment-and-blocklist](lessons/lesson-yaml-parser-inline-comment-and-blocklist.md) — `[tooling, parser, yaml, frontmatter]` — 手写 YAML 子集 parser 必须覆盖 inline-comment + block-list 两种形态 — src: `case/2026-04-20-wave3-tooling`
- [lesson-architecture-critique](lessons/lesson-architecture-critique.md) — `[architecture, refactor, self-reflection, wave5, tech-debt]` — Wave 5 抽 `tools/_common.py`；10 条架构痛点清单（DRY、状态机、分类器、规则边界…） — src: `case/2026-04-20-wave5-close`

## Pitfalls (`pitfalls/`)
- [wiki-seed-page-tbd-blind-answer](pitfalls/wiki-seed-page-tbd-blind-answer.md) — `[bootstrap, wiki, confidence, seed-page]` — 种子页 TBD 段易被当权威事实；遇 draft 必须降权 — src: `case/2026-04-20-porting-selfcheck`
- [pitfall-block-size-alignment](pitfalls/pitfall-block-size-alignment.md) — `[inference, vllm, block-size, memory, alignment]` — vLLM/SGLang 在昇腾上 block-size 必设 64/128，默认 16 直接崩 — src: `skill/ascend-troubleshoot/references/knowledge_base.md#INF-002`
- [pitfall-traceback-as-version](pitfalls/pitfall-traceback-as-version.md) — `[tooling, subprocess, version-detection]` — 用 `python -c "import X;print(X.__version__)"` 探测时，必须过滤 Traceback/ImportError 等失败标记 — src: `case/2026-04-20-wave3-tooling`
- [pitfall-tool-name-vs-intent-verb](pitfalls/pitfall-tool-name-vs-intent-verb.md) — `[routing, classifier, bench, keyword-bag, intent-detection]` — 关键词 bag 路由无法区分"提到工具 X"和"用工具 X 做 Y"；bench 81.2% 上限的根因 — src: `case/2026-04-21-wave6`
- [pitfall-cross-session-state-amnesia](pitfalls/pitfall-cross-session-state-amnesia.md) — `[self-reflection, session, ground-truth, ls-before-claim, concurrent-sessions]` — compaction summary + 副 session 并发会让主 session 说出事实错误；写量化断言前必须 `ls` verify — src: `case/2026-04-22-wave8`

## Preferences (`preferences/`)
_暂无条目。_

---

## 维护约定

- 新增条目时在对应小节**追加一行**，模板如下（`KIND` 为 `facts` / `lessons` / `pitfalls` / `preferences` 之一；`ID` 为条目的 kebab-id）：

  ```
  - `ID` → `KIND/ID.md` — `[tag1, tag2]` — 一句话摘要 — src: `case/…` 或 `user-confirmed`
  ```

  实际条目用 Markdown 链接指向真实文件。示例（只在 preferences/ 下存在 pref-quant-w8a8.md 时才应出现）：

  ```
  - [pref-quant-w8a8](preferences/pref-quant-w8a8.md) — [quantization, inference] — 偏好 W8A8 — src: case/2026-04-20-xxx
  ```
- 过期（超过 `ttl_days` 未 reverify）条目前面加 `⚠️`。
- 被取代的条目移到 [`archive/`](#archive) 小节（独立 `archive/` 目录可选）。
- 单文件行数 > 300 建议拆分主题子索引。

## Archive
_无_
