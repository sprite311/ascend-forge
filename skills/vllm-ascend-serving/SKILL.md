---
name: vllm-ascend-serving
description: 用 vLLM-Ascend 拉起 OpenAI 兼容推理服务
trigger: ["vllm", "vllm-ascend", "openai api", "page attention"]
applies_to:
  hardware: [910B]
  software: [vllm-ascend, CANN>=8.0, torch_npu]
version: 0.1.0
owners: [ascend-deployer]
safety: read-write
---

# vLLM-Ascend Serving SOP

## 前置
- `pip install vllm-ascend` 对应分支
- 模型是 HF 格式，架构 vLLM 支持（查 `wiki/software/vllm-ascend.md` 支持表）

## 步骤
```bash
python -m vllm.entrypoints.openai.api_server \
  --model /path/to/hf_weights \
  --tensor-parallel-size 8 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.9 \
  --port 8000
```

说明：
- `--gpu-memory-utilization` 在 Ascend 上同样生效（名字没改），控制 HBM 预留
- `--enforce-eager` 排查问题时先关图模式
- 量化：`--quantization awq` 或 `--quantization w8a8_dynamic`

## 验证
```bash
curl http://localhost:8000/v1/models
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<name>","prompt":"hello","max_tokens":16}'
```

## 常见坑
- vLLM 版本 vs vllm-ascend 分支不一致 → import 报错
- CANN 版本老于要求 → `aclrtMalloc` 崩
- 长序列 OOM → 降 `--max-model-len` 或 enable chunked prefill

## 参考
- `wiki/software/vllm-ascend.md`
- [vllm-project/vllm-ascend](https://github.com/vllm-project/vllm-ascend)
