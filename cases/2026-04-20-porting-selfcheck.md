---
id: 2026-04-20-porting-selfcheck
date: 2026-04-20
duration_min: 6
subagents: [knowledge-curator]
models: []
hardware: [910b]
software: [mindie]
outcome: resolved
tags: [selfcheck, bootstrap, porting, v0.1]
extracted:
  memory: [pitfall-wiki-seed-page-tbd-blind-answer]
  wiki: []
  rules: [seed-critical-wiki-before-first-use]
---

## 问题
按 `docs/PORTING.md §8` 的 5 步自检跑一遍 ascend-forge v0.1 骨架，验证：
Claude Code 能否正确路由 subagent、命中 skill trigger、遵守诚实原则（不对"规格未登记"的问题瞎编）、
任务结束后 curator 能跑起来并产出合规知识条目。

## 过程（时间线）
- **00:00** 开场必读：rules/ACTIVE.md（9 条）、memory/INDEX.md（空）、wiki/INDEX.md（10 页登记）加载完毕。
- **00:01** Step 1：扫 `agents/*.md` 的 frontmatter，成功列出 7 个 subagent（6 业务 + 1 curator）。✅
- **00:02** Step 2：用户问"910B 有多少 AICore？"。正确路由到 `wiki/hardware/910b.md`——发现"规格"段 AICore 数 = `TBD`。按 R010（要 source）与诚实原则，agent 拒绝瞎编，明确说明 wiki 未登记 + 训练记忆约 25 的低置信度回答 + 建议用 `npu-smi info -t board -i 0` 与官方白皮书核实后回填。✅
- **00:03** Step 3：问"怎么起 MindIE 服务"。trigger 匹配器得分 = 2（mindie + openai api），命中 `skills/mindie-deployment/SKILL.md`，路由到 `@ascend-deployer`。✅
- **00:04** Step 4：curator 上场（本 case 即其产物）。
- **00:05** Step 5：留给下一段 `git status` / `git diff`。

## 根因（本次暴露的真问题）
wiki 种子页（hardware/910b.md、310p.md、software/cann.md、software/mindie.md 等）全部带 `TBD`
占位。这在"骨架阶段"是合理的，但**上生产前**若不填满，agent 遇到具体提问会频繁触发"低置信度拒答"，
用户体验差。且用户可能不理解为什么空页也被登记在 INDEX 里。

## 修复
- 短期：把 910b / 310p / cann / mindie / torch-npu / vllm-ascend / mindformers / mindspore
  这 8 个种子页的"规格 / 版本矩阵 / 安装要点"三段在一次专门的"种子 session"里填完，
  来源用 `source: official-doc:<url>`。
- 长期：rule proposal（见下）约束"wiki 页 status=draft 时主 agent 必须在回答开头标注 low confidence"。

## 复盘
- **做得好**：trigger 匹配器、subagent 路由、诚实原则全部按设计生效。
- **可以更好**：wiki 的 `status: draft` 字段在 frontmatter 里存在，但主 agent 路径还没显式用它降低置信度——应该在 system prompt 里补一条"遇 draft 页必降权 + 必提示用户"。

## Metrics
- 工具调用数: 4（Read × 1 + Bash × 3）
- 失败重试数: 0
- 总耗时 (min): 约 6

## Curator Log
- wrote: `cases/2026-04-20-porting-selfcheck.md`（本 case）
- wrote: `memory/pitfalls/wiki-seed-page-tbd-blind-answer.md`
- appended: `memory/INDEX.md`（pitfalls 小节）
- proposed: `rules/proposals/2026-04-20-seed-critical-wiki-before-first-use.md`
