---
id: fact-ascend-three-piece-matrix
kind: fact
tags: [version, torch, torch-npu, cann, compat-matrix, env]
source: skill/ascend-troubleshoot/references/version_matrix.md (user-confirmed)
created_at: 2026-04-20
verified_at: 2026-04-20
confidence: high
ttl_days: 180
related_wiki: [cann, torch-npu, 910b]
---

## 事实
昇腾环境装框架必须按 **PyTorch × torch_npu × CANN × Python** 严格对应；
任何一档错开 90% 以上会 segfault 或 `libhccl.so: undefined symbol`。

### 当前权威版本矩阵（截至 2026-04）

| PyTorch | torch_npu | CANN       | Python    | 备注                  |
|---------|-----------|------------|-----------|-----------------------|
| 2.1.0   | 2.1.0     | 8.0.RC1+   | 3.8 – 3.10 | LLaMA-Factory 推荐    |
| 2.2.0   | 2.2.0     | 8.0.RC3+   | 3.8 – 3.10 |                       |
| 2.3.1   | 2.3.1     | 8.0.T13+   | 3.8 – 3.11 |                       |
| 2.4.0   | 2.4.0     | 8.3.RC1+   | 3.8 – 3.11 | SGLang / vLLM 推荐    |
| 2.5.0   | 2.5.0     | 8.3.RC1+   | 3.9 – 3.12 | 最新，部分框架未跟进  |

## 参考
- [`wiki/software/cann.md`](../../wiki/software/cann.md#核心三件套pytorch--torch_npu--cann--python) — 权威页
- [`wiki/errors/torch-npu-cann-version-mismatch.md`](../../wiki/errors/torch-npu-cann-version-mismatch.md) — 错配表现与修复
- [case 2026-04-20-troubleshoot-migration-wave1](../../cases/2026-04-20-troubleshoot-migration-wave1.md)

## 再验证建议
每出新 CANN minor / torch_npu 主版本时用 `cat /usr/local/Ascend/ascend-toolkit/latest/version.cfg` 核实，
并刷新本页 + `wiki/software/cann.md` 的 `last_verified`。
