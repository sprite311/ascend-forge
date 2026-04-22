---
id: lesson-yaml-parser-inline-comment-and-blocklist
kind: lesson
tags: [tooling, parser, yaml, frontmatter, pitfall]
source: case/2026-04-20-wave3-tooling
created_at: 2026-04-20
verified_at: 2026-04-20
confidence: high
ttl_days: 365
related_wiki: []
---

## 教训：手写的 YAML frontmatter parser 必须覆盖 inline-comment + block-list 两种形态

### 背景
本仓库的 `tools/evolve.py` / `wiki_link_check.py` / `rag_index.py` 三处都有一个
轻量的 "只解析 frontmatter" 的 parser（~15 行）。第一版只处理
"key: value" 单行 + `[a, b, c]` inline list 两种形态，在真实数据上踩了两次坑：

1. `status: pending   # pending|accepted|rejected|superseded` — 整段带进 value。
2. `sources:\n  - https://...\n  - ...` — block-list 的 `- ` 行被当成新 kv 对，
   结果 JSONL 里出现 `"- https": "//..."` 这种错位 key。

### 经验
手写的"YAML 子集" parser 最少必须覆盖：

| 形态 | 例 | 处理 |
|-----|----|------|
| 单值 | `k: v` | trivial |
| inline 注释 | `k: v  # note` | `re.sub(r"\s+#.*$", "", v)` — 注意**只在空白前**才剥，保护 URL `#fragment` |
| inline list | `k: [a, b]` | split by `,` + strip quotes |
| block list | `k:\n  - a\n  - b` | 用 `last_list_key` 状态机：若上一行 value 为空、当前行以 `- ` 开头，append |
| block mapping | `k:\n  sub: v` | 目前 **不**支持；若出现请改用真 YAML 库 |

### 行动
- 三处 parser 已同步修复，diff 集中在 `parse_fm` / `parse_frontmatter`。
- 下次仓库里出现 block mapping（如 `confidence: \n  level: high\n  reason: ...`），
  **必须**换 `pyyaml` 而不是继续打补丁。
- 新增 frontmatter 字段时，在 `docs/KNOWLEDGE-MODEL.md` 里明确是哪种形态，避免格式漂移。

### 判据
出现"parser 误解析"二次退化时，升级为硬依赖 `pyyaml`——写到 `requirements-tools.txt`
即可，现阶段没有 requirements 文件是刻意保持零依赖的取舍。
