---
name: msprof-profiling
description: 用 msprof / torch_npu.profiler 采集昇腾性能数据并解读
trigger: ["profiling", "msprof", "性能分析", "瓶颈"]
applies_to:
  hardware: [910B, 310P]
  software: [CANN>=7.0]
version: 0.1.0
owners: [ascend-tuner, ascend-diagnoser]
safety: read-only
---

# MSProf Profiling SOP

## 何时使用
已经能跑但"慢"或"不规律"，需要抓真实 timeline 找瓶颈。

## 采集方式 A：命令行 msprof
```bash
msprof --application="python run.py" \
       --output=./prof_out \
       --aicpu=on --ai-core=on --hccl=on \
       --task-time=on --aic-metrics=PipeUtilization
```

## 采集方式 B：torch_npu.profiler（在代码里插桩）
```python
import torch_npu
from torch_npu.profiler import profile, schedule, tensorboard_trace_handler

with profile(
    activities=[torch_npu.profiler.ProfilerActivity.CPU,
                torch_npu.profiler.ProfilerActivity.NPU],
    schedule=schedule(wait=1, warmup=1, active=3, repeat=1),
    on_trace_ready=tensorboard_trace_handler("./prof_out"),
    record_shapes=True,
) as prof:
    for step in range(10):
        forward()
        prof.step()
```

## 解读
- 打开 `prof_out/**/op_summary_*.csv`——找耗时 Top 算子
- 打开 timeline（`msprof-analyze` 或 TensorBoard）看：
  - AICore 利用率 < 70% → 可能 host 侧 bound / 小算子
  - HBM 带宽打满 → 访存 bound，考虑量化 / 融合
  - HCCL 时间段占比高 → 通信 bound，考虑减少同步 / 增加 overlap

## 输出模板（附到 case）
```markdown
### Profiling summary
- 总步耗: XX ms
- AICore util (avg / P95): XX / XX
- Top-3 算子:
  - OpA: XX ms (XX%)
  - OpB: XX ms (XX%)
  - OpC: XX ms (XX%)
- 结论: <瓶颈假设>
```

## 参考
- `wiki/operators/` 收录的性能特征
- 官方 msprof 文档
