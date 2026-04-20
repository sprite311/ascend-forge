---
name: benchmark-baseline
description: 建立模型×引擎×硬件×软件栈的可复现性能基线
trigger: ["benchmark", "基线", "性能测试", "tps", "ttft", "tpot"]
applies_to:
  hardware: [910B, 310P]
version: 0.1.0
owners: [ascend-benchmarker]
safety: read-only
---

# 基准测试 SOP

## 规定动作

**每次 benchmark 都必须记录环境指纹**：
```
- 硬件: 910B x N（卡号）
- 驱动 / 固件版本
- CANN 版本
- 引擎（MindIE / vLLM-Ascend / MindFormers）版本
- 模型 + 权重 hash
- 本仓库 commit sha
- 输入负载（ShareGPT? 固定长度?）
- 并发 / max_num_seqs
```

## 负载类型

| 目的 | 负载 |
|---|---|
| 吞吐 | ShareGPT / 业务 trace 回放 |
| TTFT | 固定 prefill 长度 256/1024/4096 |
| TPOT | 长 decode（固定 prefill + 生成 N tokens） |
| 稳定性 | 持续 30 min 看 P99、显存漂移 |

## 常用工具

- vLLM: `benchmark_serving.py`（官方）
- 通用：`wrk` / `hey` / `locust` + 自写 prompt generator
- 官方：`msit` 可能含 benchmark 子命令（查 wiki）

## 输出格式

严格按 `agents/ascend-benchmarker.md` 的小节模板追加到 `wiki/models/<id>.md#performance`。

## 回归告警

- 相同配置下 TPS 比上次基线差 > 5% → 建 case 叫 tuner
- 任何 P99 突起 > 2× 基线 → 建 case 叫 diagnoser
