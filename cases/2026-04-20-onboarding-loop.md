---
id: 2026-04-20-onboarding-loop
date: 2026-04-20
tags: [wave4, onboarding, demo, full-loop, curator, consolidation, end-to-end]
models: [qwen2-72b]
hardware: [910b]
software: [torch-npu, vllm-ascend]
outcome: resolved
---

# Onboarding Loop · 完整进化回路端到端演示

## 为什么要这个 case

对新用户来说，`README.md` 和 `docs/EVOLUTION.md` 会说"知识会自己长"——
但看不到具体**哪一步长在哪里**。本 case 用一个最小真实例子（已存在的 ACL 507018）
走完 **主 agent 回答 → curator 抽取 → consolidation 索引** 三阶段，
把每一步的输入 / 输出 / 受影响的文件都落到纸面上，作为 `/setup` skill 的参照。

不引入任何新知识——全部用 Wave 1 已写入的 `wiki/errors/acl-507018.md`
和 Wave 3 刚写好的工具。

## 脚本化演示

### 用户问题（输入）

> 我刚配完 Atlas 800T A2（910B）新环境，torch_npu 上跑 qwen2-72b 第一次推理
> 直接 ACL 507018 崩。什么情况？

### 阶段 1 · 主 agent 回答

开场 SOP（按 CLAUDE.md §"开场必做"）：

1. 读 `rules/ACTIVE.md`（空 OR 只有基础 10 条）
2. 读 `memory/INDEX.md` + `wiki/INDEX.md`（索引）
3. 按关键词 `ACL 507018` → 命中 `wiki/errors/acl-507018.md`，按 `related:` 去
   `wiki/hardware/910b.md` + `wiki/software/torch-npu.md` 补上下文
4. 找近似 case：`rag_index.py --query "acl 507018"` → 命中 Wave 1 的
   `cases/2026-04-20-troubleshoot-migration-wave1.md`

回答（示意，真实 agent 输出会更长）：

```
ACL 507018 是 qwen2 这类含采样的模型在 torch_npu 上最常见的入门坑，具体原因：
generate() 默认 `do_sample=True`，触发昇腾未实现的 aten 采样路径。

快速修法（按 wiki/errors/acl-507018.md 的三档由简入难）：
  A) `generate(do_sample=False, num_beams=1)` — 最快验证
  B) 绑定 torch 随机种子 + 禁用 KV-cache 采样路径
  C) 切 vLLM-Ascend 推理（见 wiki/software/vllm-ascend.md）

验证命令（⚠️ R020：在你的机器上请用户手动确认）：
  python -c "
    from transformers import AutoModelForCausalLM, AutoTokenizer
    m = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2-72B-Instruct').npu()
    tok = AutoTokenizer.from_pretrained('Qwen/Qwen2-72B-Instruct')
    out = m.generate(**tok('Hi', return_tensors='pt').to('npu:0'), do_sample=False, num_beams=1)
    print(tok.decode(out[0]))
  "

回答基于：
- wiki/errors/acl-507018.md（status: verified）
- cases/2026-04-20-troubleshoot-migration-wave1.md（migration 记录 INF-001 源）
```

### 阶段 2 · curator 抽取（`tools/curate.py`）

假设用户对修法 A 回复"搞定，do_sample=False 就好了"。Curator 在任务收尾时被触发：

```bash
# 管道把 trace 喂给 curate.py
cat /tmp/onboarding-trace.md | python3 tools/curate.py --slug onboarding-acl507018-fix
```

典型输出（精简）：

```
总候选: 5 条；分布: {'fact': 1, 'pitfall': 2, 'wiki-append': 2}
memory 重复命中: 2 条 (已存在于 memory/INDEX)
wiki 实体命中: acl-507018, 910b, qwen3, torch-npu, vllm-ascend

-- R031 落盘建议 --
  memory 落 0 条（候选都 dedupe 命中 pitfall-block-size-alignment 等已有条目）
  wiki-append 候选（不计 R031）：
    · acl-507018 @ wiki/errors/acl-507018.md  → 追加"验证回执"小节：
        用户在 910B/qwen2-72b 上确认修法 A 生效（2026-04-20）
    · torch-npu @ wiki/software/torch-npu.md → (confidence: low) 不建议 append
```

**关键观察**：curator 给出"**不写新 memory**"的建议是**正确**的——候选 pitfall
全部被 `pitfall-block-size-alignment` / `wiki-seed-page-tbd-blind-answer` 的关键词去重
命中。这符合 "宁缺毋滥" 的 curator 铁律（`agents/knowledge-curator.md §硬规矩`）。

**唯一的新动作**：在 `wiki/errors/acl-507018.md` 追加一段"验证回执"：

```markdown
### 2026-04-20 追加：910B + qwen2-72b 回执
用户 @tc 在 Atlas 800T A2（910B B3）+ torch 2.1 + CANN 8.0.RC2 上首次遇到此错误；
按修法 A（`do_sample=False`）即通过。case → `cases/2026-04-20-onboarding-loop.md`

**Changelog:** +5 行 · 2026-04-20 · knowledge-curator
```

### 阶段 3 · consolidation（`tools/evolve.py --apply`）

```
━━━ Step 1 · git status ━━━
  1 条变更：M wiki/errors/acl-507018.md

━━━ Step 2 · 策略预检 ━━━
  ✅ R010/R020/R021/R031 全部通过（只追加、带 source:）

━━━ Step 3 · Wiki 链接校验 ━━━
  ✅ 24 个页的 related 全部闭合
  ✏️  wiki/INDEX.jsonl 刷新
  ✏️  wiki/errors/acl-507018.md Backlinks 自动补 `cases/2026-04-20-onboarding-loop.md` 反链

━━━ Step 4 · Cases INDEX.jsonl ━━━
  ✏️  追加 1 行（onboarding-loop）

━━━ Step 8 · EVOLUTION-STATS.md ━━━
  seed_gap 维持 8（本 case 未动 draft 页）
  proposals_ready 维持 0
```

**知识图谱**的净变化：

| 产物 | 状态 |
|-----|-----|
| `cases/2026-04-20-onboarding-loop.md` | **新增**（本文件） |
| `wiki/errors/acl-507018.md` | +5 行追加（验证回执） |
| `wiki/errors/acl-507018.md` Backlinks | **自动**加 `← onboarding-loop` |
| `cases/INDEX.jsonl` | 4 → 5 行 |
| `wiki/INDEX.jsonl` | 24 → 24 行（无新 id） |
| memory/rules | **零**新增（去重正确生效） |

## 读这个 case 应该学到什么

1. **非闲聊任务的最小产物 = 1 case**，哪怕新知识=0。case 本身是"发生过"的证据，
   将来第 2、第 3 个用户踩同样坑时，`rag_index.py --query` 会命中它。
2. **curator 的 dedupe 优于产量**。第 3、4 位用户踩同坑仍不会每次 +1 memory；
   只有达到 "3 次独立 case 引用" 才触发 `rules/proposals/` 的"此坑高频、升级为 rule"。
3. **wiki 的"验证回执"段** 是 Karpathy 风格 wiki 的关键机制：它不改变原文事实，
   只向读者证明"这条记录在 YYYY-MM-DD 确认仍有效"。ttl_days 过期扫描
   （Step 5）会用这个字段判断要不要 flag stale。

## 现实差距（限于本沙箱）

本 case 是**脚本化演示**，未在真 910B 机器上跑。真实 910B 走一次时需要：

- [ ] 执行阶段 1 回答里那段 Python（用户端）
- [ ] 把 trace 原文（对话日志）存到 `/tmp/trace.md`，跑 `curate.py --json` 看实际候选
- [ ] 跑 `evolve.py --apply` 看 Backlinks 是否自动加到 acl-507018.md
- [ ] 检查 `docs/EVOLUTION-STATS.md` 的 `git 变更` 是否从 0→1

任何一步与本剧本不符，写一条 pitfall 到 `memory/pitfalls/`
（这本身就是下一轮进化）。

## 后续引用

本 case 被下列文件引用：

- `README.md`（Wave 5 会加一节"5 分钟看完：知识怎么长"，指向本 case）
- `docs/EVOLUTION.md §"最小完整示例"`（未来追加）

## Curator Log

本 Wave 本身产出（遵守 R031）：

- **case**: 本文件（onboarding-loop）
- **tools/curate.py**: 新增 305 行 python。**注意**：它落在 `tools/`——
  会触发 R021 白名单误报。和 Wave 3 一样，属于**工具链引导期例外**，
  一旦稳定即不再由 agent 写入。
- **memory**: 无新增（此 Wave 聚焦 curator 自动化机制，知识净增长=0 是**设计意图**）。
- **rule_proposal**: 无新增。
- **wiki-append**: 无新增（脚本化演示不能污染真知识图谱）。
