# Skills Index

> trigger → skill 的快查表，由 consolidation 维护。手改请同时改对应 `SKILL.md` 的 `trigger:`。

| Skill | Trigger（或关系） | Owners |
|---|---|---|
| [model-adaptation](model-adaptation/SKILL.md) | 适配 / 迁移 / torch_npu / mindspore / mindformers | ascend-adapter |
| [operator-replacement](operator-replacement/SKILL.md) | 算子 / operator / not implemented / aten:: | ascend-adapter, ascend-tuner |
| [precision-alignment](precision-alignment/SKILL.md) | 精度 / 对齐 / diff / logits / nan / cosine | ascend-adapter, ascend-diagnoser |
| [mindie-deployment](mindie-deployment/SKILL.md) | mindie / 推理服务 / openai api / 起服务 | ascend-deployer |
| [vllm-ascend-serving](vllm-ascend-serving/SKILL.md) | vllm / vllm-ascend / openai api / page attention | ascend-deployer |
| [mindformers-training](mindformers-training/SKILL.md) | mindformers / 训练 / sft / lora / finetune | ascend-deployer |
| [msprof-profiling](msprof-profiling/SKILL.md) | profiling / msprof / 性能分析 / 瓶颈 | ascend-tuner, ascend-diagnoser |
| [memory-optimization](memory-optimization/SKILL.md) | oom / 显存 / kv cache / acl_error_500002 / memory | ascend-tuner |
| [benchmark-baseline](benchmark-baseline/SKILL.md) | benchmark / 基线 / 性能测试 / tps / ttft / tpot | ascend-benchmarker |
| [ascend-troubleshoot](ascend-troubleshoot/SKILL.md) | 昇腾 / Ascend / NPU / CANN / torch_npu / MindSpore / Atlas / 910B / 910C / 310P / MindIE / npu-smi / HCCL / AscendCL | ascend-diagnoser |
| [knowledge-capture](knowledge-capture/SKILL.md) | task_end / /evolve / /curate / 记住 / 以后都 / 我偏好 | knowledge-curator |

---

## 已有的大块知识（待分裂迁移到 wiki）

`ascend-troubleshoot/references/knowledge_base.md` 是一份 900+ 行的结构化故障库（按 ENV / 容器 / CUDA 迁移 / 框架 / 训练 / 推理 / HCCL / OOM / 调优 / 模型转换 / 特定框架 分 11 类）。

**建议迁移路径**（由 `knowledge-curator` 在后续 consolidation 中逐批完成）：

| 该文件的内容 | 迁移目标 |
|---|---|
| 每个 `ENV-xxx` / `ACL-xxx` / `HCCL-xxx` 条目 | `wiki/errors/<signature>.md`（一错误一页） |
| 版本矩阵（`version_matrix.md`） | `wiki/software/cann.md` 的版本矩阵小节 |
| 通用 debug 流程（`general_debug.md`） | `wiki/playbooks/general-debug.md` |
| 框架适配章节 | 分别并入 `wiki/software/<framework>.md` |
| 具体坑 + 规避 | `memory/pitfalls/<id>.md`，源 `source: skill/ascend-troubleshoot` |

迁移要**保留原文件不删**（它仍是 skill 的参考材料），只是把条目拆成独立 wiki 页便于按签名精确命中。
