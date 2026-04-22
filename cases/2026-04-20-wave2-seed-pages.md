---
id: 2026-04-20-wave2-seed-pages
date: 2026-04-20
duration_min: 22
subagents: [knowledge-curator]
models: [qwen3, deepseek-v3, llama3]
hardware: [910B, 910C, 310P, 310B]
software: [cann, torch-npu, mindie, vllm-ascend, mindspore, mindformers]
outcome: resolved
tags: [migration, wave2, seed-pages, wiki, content-backfill]
extracted:
  memory: []
  wiki:
    - hardware/910b.md (backfill)
    - hardware/310p.md (backfill)
    - software/mindie.md (backfill)
    - software/mindspore.md (backfill)
    - software/mindformers.md (backfill)
    - software/torch-npu.md (backfill)
    - software/vllm-ascend.md (backfill)
    - models/qwen3.md (new)
    - models/deepseek-v3.md (new)
    - models/llama3.md (new)
  rules: []
---

## 问题
Wave 1 迁完了错误库和 playbook，但**种子页（hardware / software）还是半空**：
910b / 310p 只有 TBD、mindie 只有骨架、mindspore / mindformers / torch-npu / vllm-ascend 全是"占位页"。
这导致：
- 用户问 "Qwen3 怎么在 910B 跑"时，agent 只能跳到 mindie.md 的空壳页
- 种子页 `related:` 断链（本次发现 `910c` / `310b` 在 Wave 1 `related:` 里引用但缺页）

Wave 2 的目标：**把 7 个种子页填实**（用公开资料口径 + 明确低置信度 + 给出核实命令），
同时补 **3 个热门模型页**（Qwen3 / DeepSeek-V3 / Llama3）。

## 过程（时间线）
- **00:00** Wave 1 validation 意外发现 `910c` / `310b` 缺页，临时创建 2 个 draft 种子页解围。
- **00:03** 填 `hardware/910b.md`：补 SKU（B1-B4）、HBM / AICore / HCCS 说明、软件版本映射表、常见坑 6 链接。
- **00:06** 填 `hardware/310p.md`：Atlas 300I/Duo/Pro + 500 Pro SKU、推理三条路径（OM / ONNX RT / MindIE）。
- **00:09** 填 `software/mindie.md`：ATB / PagedAttention / continuous batching、完整启动命令 + config.json 片段。
- **00:12** 填 `software/mindspore.md`：图模式 / PyNative / jit_level / run_check + 静态图坑。
- **00:14** 填 `software/mindformers.md`：模型家族清单、msrun / rank_table 启动、三维并行配置要点。
- **00:16** 填 `software/torch-npu.md`：权威三件套矩阵、三种使用模式（手动 / transfer_to_npu / monkey-patch）、辅助依赖。
- **00:18** 填 `software/vllm-ascend.md`：昇腾特有调参表（block-size / max-total-tokens / mem-fraction）、与 CUDA vLLM 差异。
- **00:20** 建 `models/qwen3.md` / `models/deepseek-v3.md` / `models/llama3.md`：架构 + 昇腾适配状态 + 部署命令 + 显存预算。
- **00:21** 更新 `wiki/INDEX.md` 的 Hardware / Software / Models 小节。
- **00:22** 验证待跑。

## 写入清单

| Target                               | Kind     | 动作       |
|--------------------------------------|----------|------------|
| `wiki/hardware/910b.md`              | hardware | backfill   |
| `wiki/hardware/310p.md`              | hardware | backfill   |
| `wiki/software/mindie.md`            | software | backfill   |
| `wiki/software/mindspore.md`         | software | backfill   |
| `wiki/software/mindformers.md`       | software | backfill   |
| `wiki/software/torch-npu.md`         | software | backfill   |
| `wiki/software/vllm-ascend.md`       | software | backfill   |
| `wiki/models/qwen3.md`               | model    | new        |
| `wiki/models/deepseek-v3.md`         | model    | new        |
| `wiki/models/llama3.md`              | model    | new        |
| `wiki/INDEX.md`                      | index    | append     |

## 置信度声明
- **版本矩阵 / 安装命令 / CLI 参数**：来自 `skill/ascend-troubleshoot/references/version_matrix.md`（用户确认）+ 上游 repo README，**高置信度**。
- **具体硬件规格数字（AICore 数、TFLOPS）**：公开市场资料口径，**中置信度**；已在页面显式标注"请用 `npu-smi info -t board` 核实"。
- **模型适配状态 / 显存预算**：基于昇腾社区常见部署经验与 knowledge_base.md OOM-001 估算，**中置信度**；精度 / 性能基线空着，待真实 benchmark case 回填。

## 复盘
- **做得好**：所有页面加了置信度标识、核实命令、常见坑反链。填完后 `wiki/errors/` 与种子页形成闭环（A→B→C→A）。
- **可以更好**：`wiki/operators/` 的 flash-attention / rotary-embedding 还是占位；Wave 3+ 迁；`models/*.md` 的基线全部靠后续 case 回填，这是设计决策（不瞎编性能数字）。

## Metrics
- 工具调用数: ~22
- 失败重试数: 1（`Write` 一次因未先 Read 被拒，随后补读）
- 总耗时 (min): ~22
- 新增 wiki 页: 3（models）
- 修改 wiki 页: 8（hardware×2, software×5, INDEX）
- 新增 memory: 0
- 新增 rule proposal: 0
- 新增 case: 1（本文件）

## Curator Log
- appended: `wiki/hardware/910b.md`（Wave 2 回填段 + Changelog）
- appended: `wiki/hardware/310p.md`
- appended: `wiki/software/mindie.md`
- appended: `wiki/software/mindspore.md`
- appended: `wiki/software/mindformers.md`
- appended: `wiki/software/torch-npu.md`
- appended: `wiki/software/vllm-ascend.md`
- wrote: `wiki/models/qwen3.md`
- wrote: `wiki/models/deepseek-v3.md`
- wrote: `wiki/models/llama3.md`
- appended: `wiki/INDEX.md`（Models 小节）
