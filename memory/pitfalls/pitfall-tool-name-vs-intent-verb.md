---
id: pitfall-tool-name-vs-intent-verb
date: 2026-04-22
tags: [routing, classifier, bench, keyword-bag, intent-detection]
status: active
source: case/2026-04-21-wave6
ttl_days: 365
verified_at: 2026-04-22
---

# Pitfall：关键词路由中"工具名 vs 意图动词"的冲突

## 现象

主 agent 看到用户问题，决定路由到哪个 subagent 时，如果分流器是**关键词+权重 bag-of-words**（例如 `tools/bench.py` 现在的实现），会在下面这一类问法上**系统性地路由错**：

```
"vLLM-Ascend 的 prefill 慢得离谱，怎么调？"
"MindIE 部署后 ACL 507013，用户端无响应"
"torch_npu 一 import 就 segfault"
"升了 CANN 后 ACL 507018"
```

这些问题的**意图**（"调参" / "定位报错" / "查崩溃" / "环境变化归因"）和**提及的工具名**分属**不同 subagent**：

| 问题示例 | 工具名（强词，3 分） | 意图动词（本应压过工具名） | 实际路由（错） | 应该路由 |
|---|---|---|---|---|
| `vLLM-Ascend ... prefill 慢，怎么调` | `vLLM-Ascend` (deployer) | `慢 / 调 / prefill` (tuner) | deployer | tuner |
| `MindIE 部署后 ACL error` | `MindIE / 部署` (deployer×2) | `ACL / error` (diagnoser) | deployer | diagnoser |
| `torch_npu import segfault` | `torch_npu` (adapter) | `segfault / 崩` (diagnoser) | adapter | diagnoser |
| `升了 CANN 后 ACL 507018` | `CANN` (env-doctor) + `ACL` (diagnoser) | `升了 ... 后` 时间因果指向 env | diagnoser | env-doctor |

Wave 6 的 bench 32 题里，此模式导致 6 条（~19%）失败，使 bench 通过率卡在 81.2% 过不了 90% 门槛。

## 根因

关键词 bag 有三层缺陷：

1. **无"是提到 X"vs"在用 X 做 Y"的区分**——"vLLM-Ascend 的 prefill"里，vLLM-Ascend 是**被操作对象**，不是任务本身。
2. **无负向语义**——"`不`报错"里的"报错"会正向命中 diagnoser。
3. **无时间 / 因果语义**——"升了 CANN 后 ACL error" 里的"后"暗示 CANN 升级是原因，但分类器只看词汇频率。

## 缓解策略（按代价递增）

### 策略 A：给意图动词加权重（临时补丁）

对 `tune / 调 / 调优 / 优化 / 诊断 / 定位` 这类动词加高权重（5-7 分），使之能压过"工具名 3 分"的信号。代价：容易把"我部署时遇到 tune 相关选项"这种也拉错方向。

```python
# 例：tools/bench.py KEYWORDS 里
"ascend-tuner": [
    # ...
    ("调", 1),           # Wave 6.1 加的，权重故意低
    ("调参", 4),         # 潜在：再加
    ("调优", 5),         # 潜在：再加
],
```

**评估**：Wave 6 只加了 `调(1)` 这一个小权重，因为大权重会让"真的是部署任务但提到'调端口'"这类也转成 tuner。**cost/benefit 不明**；先不加。

### 策略 B：引"意图前缀"的轻规则（中等投入）

在分类器前加一层固定模式匹配：
- `X 的 Y 慢/快/卡/OOM`  → tuner（X 是工具，Y 是被调对象）
- `X 的 Y 报错/崩/错误`   → diagnoser
- `升/装/换 X 后 Y 出问题` → env-doctor

这类规则能精准捕上面 4 个例子，且代价是一个可读的 dict。但规则数会膨胀，维护成本 > 原关键词表。

### 策略 C：真正的语义路由（最高投入，最优解）

把 15-30 条 golden 题当 few-shot，调一次 LLM 或 embedding-NN 做意图分类：
- 选项 C1：让主 agent 自己 LLM-route（每次多一次模型调用；但本来就要过一次 LLM 脑子理解问题）
- 选项 C2：本地嵌入模型（e.g. BGE-small，~33M 参数，CPU 可跑）+ kNN 分类

**评估**：Ascend-Forge 当前"纯 stdlib / 纯文件"的设计原则拒绝引入 embedding 模型依赖；选项 C1 在 Claude Code 场景里**本来就已经发生**（路由决策是 LLM 做的，`bench.py` 只是 approx）。结论：**真实的主 agent 路由远好于 bench.py**，bench 的 81.2% 不代表用户体验的 81.2%。

## 给 bench.py 的诚实结论

- **bench.py 的 81.2% 是关键词 bag 路由的真实上限，不是主 agent 的真实水平。**
- bench 的价值是"发现关键词表的 blind spot"，不是给主 agent 打分。
- 以后修改 `agents/*.md` 或 `CLAUDE.md` 路由表后，bench 过不了 90% 不应 block merge；只应做**回归信号**——新版本 bench 分比老版本掉 5% 以上才 flag。

## 给主 agent 的可操作提示

当用户问题里出现"工具名 + 意图动词"组合时，主 agent 自己做决策，不应被 bench 的弱分类器干扰：

```
识别模式：句中出现 <工具名> 的 <x>、用 <工具名> 后 <x>
→ 意图词在 <x> 里，不在工具名里。按意图路由。
```

## 相关

- `cases/2026-04-21-wave6.md` — 6 条失败 bench 的详单
- `memory/lessons/lesson-architecture-critique.md` #4 — 首次点出"bench 过拟合"
- `tools/bench.py` — 当前的关键词表
- `bench/golden-questions.yaml` q21 / q23 / q27 / q29 / q30 / q31 — 6 条反例题
