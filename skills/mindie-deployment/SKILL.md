---
name: mindie-deployment
description: 用 MindIE 把模型拉起为推理服务（含 OpenAI 兼容 API）
trigger:
  - "mindie"
  - "推理服务"
  - "openai api"
  - "起服务"
applies_to:
  hardware: [910B, 310P]
  software: [MindIE>=1.0, CANN>=7.0]
version: 0.1.0
owners: [ascend-deployer]
safety: read-write
---

# MindIE 部署 SOP

## 前置

- 环境体检过 (`@ascend-env-doctor`)
- 权重已适配到 MindIE 支持的格式（见 `wiki/software/mindie.md` 支持矩阵）
- 预估好 KV Cache 显存：`max_num_seqs × max_model_len × 2 × n_layer × head_dim × dtype_bytes`

## 步骤（骨架，细节按版本调整）

1. 准备 `config.json` / `model_config.json`，设置：
   - `modelName`、`modelWeightPath`
   - `worldSize`（TP 卡数）
   - `npuDeviceIds`
   - `maxSeqLen`、`maxInputTokenLen`、`maxBatchSize`
2. 启动 service：

   ```bash
   cd $MIES_INSTALL_PATH/latest
   ./bin/mindieservice_daemon &
   # 或
   mindie-server --config /path/to/config.json
   ```

3. 等启动日志，确认：
   - 模型 load 成功
   - 每张卡显存占用合理
   - 监听端口 UP

4. 健康检查：

   ```bash
   curl http://localhost:1025/v1/models
   curl -X POST http://localhost:1025/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"<name>","messages":[{"role":"user","content":"hi"}]}'
   ```

## 验证

- [ ] `/v1/models` 返回目标模型
- [ ] 首 token 延迟在预期区间
- [ ] 并发 N 请求无 5xx
- [ ] 日志无 ACL_ERROR / HCCL warning

## 常见坑（查 `wiki/errors/` 更全）

- **ACL_ERROR_500002** → KV Cache 超显存，降 `maxBatchSize` 或 `maxSeqLen`
- **HCCL init failed** → 多机 `HCCL_IF_IP` 未设 / 网卡不通
- **权重加载慢** → 是否从 NFS 读？先拷到本地 NVMe
- **首 token 慢** → 检查是否命中了 `prefix-cache` / prefill chunk size

## 失败回流

新坑进 `wiki/errors/` + `memory/pitfalls/`；成功的配置 → `templates/` 固化模板。

## 参考

- [MindIE 官方文档](https://www.hiascend.com/document/)
- `wiki/software/mindie.md`
- `wiki/playbooks/`
