---
name: wiki-consolidate-draft-to-stable
description: |
  周期性把 wiki 里累积了 ≥2 条真机回执的 draft 页升级为 stable。
  这是 R033 的退出通路（draft 不再无限期降权）。
  被 @knowledge-curator 在 /evolve、consolidation 或用户手动触发时使用。
trigger: ["consolidation", "/evolve", "draft to stable", "draft 升 stable", "wiki 稳定度", "wiki_stability", "wiki stability"]
applies_to:
  platform: "*"
version: 0.1.0
owners: [knowledge-curator]
safety: read-write
source: case/2026-04-22-wave8 + tools/wiki_stability.py
---

# Wiki Draft → Stable 升级 Playbook

> **用途**：把 `wiki/**` 下已经有真机回执支撑的 `status: draft` 页升级成 `stable`，
> 关掉 R033 的"永久降权"副作用。
>
> **为什么需要 skill 而不是直接跑脚本**：
> 升级决策有人工判断（回执够不够硬核、源是否可信），脚本只能挑出候选；
> 这个 SKILL.md 是把"脚本 + 判断 + 落盘 + 回执"串成可复现的 SOP。

---

## 触发条件

- `@knowledge-curator` 在 consolidation / `/evolve` 里自动跑一次扫描；或
- 用户说"跑一下 wiki 稳定度" / "看看哪些 draft 可以升了" / "/evolve"；或
- `tools/evolve.py` Step 6（如果接入）自动调用。

## 前置条件

- `tools/wiki_stability.py` 存在（判定逻辑在那里）。
- 当前工作目录是仓库根（`ls CLAUDE.md` 应成功）。
- 可写 `wiki/**`（受 `.agent/config.yaml` `write_whitelist` 约束）。

---

## 5 步 SOP

### 1. 扫描（只读）

```bash
python3 tools/wiki_stability.py
```

输出三档：
- 🟢 **READY-STABLE**：≥ 2 条日期小节 + 每条都有 `source:` 追踪 → 候选升级
- 🟡 **DRAFT-MATURING**：1 条日期小节 → 继续等
- 🔴 **PRE-DRAFT**：0 条 → 仍是纯种子页

### 2. 判断每个 🟢 候选（人工）

对每个 🟢 页，curator / 用户快速过一遍：

- [ ] 追加小节的 `source:` 是否指向真 case 或 `user-confirmed`？
- [ ] 页内还有没有 `TBD` / `?` / `待验证`？（有 → 不升）
- [ ] 近 30 天内有没有相反证据（pitfall / 回退记录）？

**不满足就跳过**，写进 case 说明为什么没升（作为 R033 的反例数据）。

### 3. 升级（写操作）

满足判断后：

```bash
python3 tools/wiki_stability.py --apply
```

工具会：
- `status: draft` → `status: stable`
- frontmatter 末追加 `promoted_to_stable_at: <今天>`
- 内容**不动**（遵守 R011 "只追加"原则的例外：只改 frontmatter 一行）

**每次 --apply 前先手动预览 diff**（工具会在终端打印）。

### 4. 记录回执

在正在进行的 case 的 Curator Log 里追加：

```markdown
- **wiki**:
  - `wiki/<kind>/<id>.md` draft → stable（promoted_to_stable_at: YYYY-MM-DD，依据 2 条 case 回执）
```

如果本次任务没有对应 case（纯 consolidation 跑），在 `cases/<today>-consolidation.md` 新建或追加。

### 5. CI / 持续门禁（可选）

```bash
python3 tools/wiki_stability.py --strict   # 🟢 未升级 → exit 2
```

接到 `tools/evolve.py` 的 Step 6 后，"有 🟢 未升级"会阻断 evolve 正常退出——强制 curator 看一眼。
当前**不默认开**，等有 ≥ 3 次真实 🟢 升级经验后再晋升为 CI 门禁（作为 evidence 支撑新规则）。

---

## 绝不

- 不把 `stable` 降回 `draft`（降级是 curator 判断，不走这条 skill）。
- 不改 wiki 正文内容——只动 frontmatter 两行。
- 不一次升 > 3 个——单次任务配额遵守 R031 的精神（即使 wiki_append 无上限，**状态翻转**需要逐个看）。
- 不绕过"判断步"直接 `--apply`——哪怕 🟢 候选只有 1 个，也要人眼过一次 `source:` 是否真。

---

## 产出（每次跑）

- **case 回执追加**：Curator Log 里列出升级了哪些 wiki 页
- **可能的 rule proposal**：如果 🟢 候选连续 3 次都"源头不可信"被跳过 → 提 R03x 提案收紧 `source:` 格式
- **可能的 pitfall**：如果某页升 stable 后很快被打脸（新 case 推翻），沉淀 `memory/pitfalls/premature-stable-<slug>.md`

---

## 与其他 skill 的关系

- `knowledge-capture`（元 skill）：每次任务结束调用；**这个 skill 是 knowledge-capture 里"wiki 追加环节"的对偶**——knowledge-capture 只增不升，本 skill 专管"升"。
- 未来的 `case-to-skill` skill：如果本 skill 发现 draft 页频繁来自同一类任务，说明该类任务应该有对应的 L4 skill 而不是只留 wiki——可作为 case-to-skill 的输入信号。

---

## 版本历史

- **v0.1.0 (2026-04-22, Wave 8 10-min-check)**：初版。基于 `tools/wiki_stability.py` 已完成的判定逻辑封装。
  验证"skill 产出形态"—— `skills/` 下的第一个 L4 playbook，关掉 Wave 8 识别的"只会回忆不会动手"缺口的第一扇口子。
