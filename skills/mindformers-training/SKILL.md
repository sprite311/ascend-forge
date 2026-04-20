---
name: mindformers-training
description: MindFormers 训练 / SFT / LoRA 流程
trigger: ["mindformers", "训练", "sft", "lora", "finetune"]
applies_to:
  hardware: [910B]
  software: [MindFormers, MindSpore>=2.3]
version: 0.1.0
owners: [ascend-deployer]
safety: read-write
---

# MindFormers 训练 SOP

## 前置
- 数据已处理为 MindRecord / parquet 格式
- 选定基础模型并落位在 `checkpoint_download/`
- 环境变量：`GLOG_v=2`、`MINDSPORE_HCCL_CONFIG_PATH`

## 步骤
1. 找到或改写对应 YAML（`configs/<model>/pretrain_<model>.yaml`），关键字段：
   - `run_mode`: `train` / `finetune`
   - `parallel_config`: dp / mp / pp
   - `runner_config`: batch_size, epoch, sink_size
2. `bash scripts/msrun_launcher.sh <yaml> <worker_num> <local_worker_num>`
3. 监控：`tail -f output/log/rank_0/info.log`

## 验证
- loss 正常下降，nan/inf 触发则自动中止
- save_interval 写出 ckpt 完整
- resume 能从 ckpt 接着训

## 常见坑
- YAML 里的 seq_length 和数据预处理不匹配 → pad/truncate 报错
- 并行配置与卡数不匹配 → 启动即挂
- ckpt 保存路径无写权限 → 训着训着炸

## 参考
- `wiki/software/mindformers.md`
- [MindFormers Gitee](https://gitee.com/mindspore/mindformers)
