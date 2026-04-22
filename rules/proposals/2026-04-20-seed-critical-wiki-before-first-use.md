---
id: seed-critical-wiki-before-first-use
proposed_at: 2026-04-20
evidence:
  - case/2026-04-20-porting-selfcheck
  - case/2026-04-20-draft-wiki-qwen3
  - case/2026-04-20-draft-wiki-flash-attention
status: promoted
proposed_by: knowledge-curator
applies_to: [主 agent, knowledge-curator]
promoted_at: 2026-04-21
promoted_to: R033
archive_ref: rules/archive/promoted-2026-04-21-seed-critical-wiki-before-first-use.md
---

> ✅ **已于 2026-04-21 晋升为 R033**。本文件保留作为 proposal 历史；
> 正式规则见 `rules/ACTIVE.md` R033；完整提案副本见
> `rules/archive/promoted-2026-04-21-seed-critical-wiki-before-first-use.md`。

## 规则
回答任何命中 wiki 页但**该页 frontmatter `status: draft`**、或被注入段落含 `TBD` 的问题时，
主 agent 必须：

1. 在回答首行标注 **`⚠️ 低置信度：wiki 为 draft，以下基于训练记忆`**（或等价提示）。
2. 给出可操作的验证命令（优先真机命令，其次官方文档链接）。
3. **不**将 `TBD` 填入 memory/facts/；只能写入 `rules/proposals/`（"待验证"）或 case 的
   "待验证"小节。

## 理由
自检 (`cases/2026-04-20-porting-selfcheck.md`) 暴露：骨架阶段 wiki 种子页"存在但未填满"
的状态普遍。若不显式降低置信度，agent 极易把训练记忆包装成"来自 wiki 的权威事实"，
污染长期知识。本规则以最小成本（5 行 prompt 追加）闭合这一漏洞。

## 生效范围
`.agent/system_prompt.md` + 所有业务 subagent 的开场 SOP 段。

## 证据门槛
当前仅 1 case 证据；按 R032 需要 ≥ 3 独立 case 才会自动晋升，否则需用户 `/rules promote` 手动确认。

## 相关
- 抵销/补充了 R010（要 source）——R010 要"能指回源"，本规则要"源不足时降权"，互补。
