---
name: knowledge-capture
description: |
  元 skill——给 knowledge-curator 用。把一次任务 trace 转成合规的
  case + memory + wiki-append + rule-proposal。
trigger: ["task_end", "/evolve", "/curate", "记住", "以后都", "我偏好"]
applies_to:
  platform: "*"
version: 0.1.0
owners: [knowledge-curator]
safety: read-write
---

# 知识采集 SOP（元 skill）

> 这是 `knowledge-curator` 的执行手册。其他 subagent 不要直接用。

## 输入

- 本次会话的原始问答
- 调用过的工具 / 命令 / 输出
- 主 agent 的最终结论（如果有）

## 7 步

1. **先写 case**（`cases/YYYY-MM-DD-<slug>.md`）——最高优先级
2. **抽候选**（每类不超 3 条）
3. **查重**：按 id / tag / 语义
4. **落盘**：受 `.agent/evolution_policy.md` 的速率 & 白名单约束
5. **补 backlinks**
6. **追加 case 的 Curator Log**（审计）
7. **向用户汇报**（bullet 列表 + 文件路径），**不** commit

## 模板：case skeleton

```markdown
---
id: {{date}}-{{slug}}
date: {{date}}
duration_min: {{n}}
subagents: [{{...}}]
models: [{{...}}]
hardware: [{{...}}]
software: [{{...}}]
outcome: resolved
tags: [{{...}}]
extracted:
  memory: []
  wiki: []
  rules: []
---

## 问题
{{用户原始问题}}

## 过程（时间线）
- 00:00 ...
- 00:05 ...

## 根因
...

## 修复
...

## 复盘
- 做得好：
- 可以更好：

## Metrics
- 工具调用数:
- 失败重试数:
- 总耗时 (min):

## Curator Log
- wrote: ...
- appended: ...
- proposed: ...
```

## 模板：memory entry

见 `docs/KNOWLEDGE-MODEL.md §2.2`。

## 模板：rule proposal

见 `docs/EVOLUTION.md §4.4`。

## 绝不

- 不写 `rules/ACTIVE.md`
- 不改 `docs/`、`.agent/`
- 不整页重写 wiki
- 不做 git commit
- 不写无 source 条目
