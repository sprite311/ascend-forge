# 昇腾 NPU 故障排查知识库

## 目录
- [一、环境安装与驱动](#一环境安装与驱动)
- [二、容器与设备挂载](#二容器与设备挂载)
- [三、CUDA 迁移到 NPU](#三cuda-迁移到-npu)
- [四、框架与依赖冲突](#四框架与依赖冲突)
- [五、模型训练问题](#五模型训练问题)
- [六、模型推理问题](#六模型推理问题)
- [七、多卡通信（HCCL）](#七多卡通信hccl)
- [八、显存与 OOM](#八显存与-oom)
- [九、性能调优](#九性能调优)
- [十、模型转换（ONNX/OM）](#十模型转换onnxom)
- [十一、特定框架适配](#十一特定框架适配)

---

## 一、环境安装与驱动

### ENV-001：固件与驱动版本不匹配

```yaml
id: ENV-001
stage: 安装
hardware: [910B, 910C, 310P, 310B]
symptom: "npu-smi info 无法查询到芯片 / mindspore.run_check() 报错"
error: "RuntimeError: Can not find available NPU device"
root_cause: |
  固件（firmware）和驱动（driver）版本必须严格对应。
  不同芯片型号有各自的驱动包，不可混用。
  常见错误：在 910B 上安装了 910C 的驱动包。
solution: |
  1. 确认芯片型号：
     cat /usr/local/Ascend/driver/version.info
     npu-smi info
  
  2. 从昇腾社区下载匹配的驱动和固件：
     https://www.hiascend.com/developer/download
     
  3. 卸载旧驱动：
     /usr/local/Ascend/driver/script/uninstall.sh
     
  4. 安装新驱动（以 910B 为例）：
     chmod +x Ascend-hdk-910b-npu-driver_24.1.rc3_linux-aarch64.run
     ./Ascend-hdk-910b-npu-driver_24.1.rc3_linux-aarch64.run --full
     
  5. 安装固件：
     chmod +x Ascend-hdk-910b-npu-firmware_7.5.0.2.220.run
     ./Ascend-hdk-910b-npu-firmware_7.5.0.2.220.run --full
     
  6. 重启服务器后验证：
     npu-smi info
verify: "npu-smi info 显示所有芯片状态为 OK，Health 为 OK"
source: "华为昇腾官方文档、CSDN 社区实测"
```

### ENV-002：CANN Toolkit 安装后环境变量未生效

```yaml
id: ENV-002
stage: 安装
hardware: [全部]
symptom: "import torch_npu 报错 / acl 命令找不到"
error: "ModuleNotFoundError: No module named 'acl' 或 ImportError: libascendcl.so: cannot open shared object file"
root_cause: |
  CANN 安装后需要 source 环境变量脚本，否则动态库路径和 Python 路径无法找到。
  容器场景中尤其容易遗漏。
solution: |
  1. 将以下内容添加到 ~/.bashrc 或容器的启动脚本中：
     source /usr/local/Ascend/ascend-toolkit/set_env.sh
     
  2. 如果使用了自定义安装路径：
     source <安装路径>/ascend-toolkit/set_env.sh
     
  3. 验证环境变量：
     echo $ASCEND_HOME_PATH      # 应输出 CANN 安装路径
     echo $LD_LIBRARY_PATH       # 应包含 ascend 相关路径
     python -c "import acl; print('ACL OK')"
     
  4. 对于 Docker 容器，在 Dockerfile 中添加：
     ENV ASCEND_HOME_PATH=/usr/local/Ascend/ascend-toolkit/latest
     ENV LD_LIBRARY_PATH=/usr/local/Ascend/ascend-toolkit/latest/lib64:$LD_LIBRARY_PATH
     ENV PYTHONPATH=/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:$PYTHONPATH
verify: "python -c \"import acl\" 无报错"
source: "昇腾官方安装文档"
```

### ENV-003：内核版本过低导致驱动安装失败

```yaml
id: ENV-003
stage: 安装
hardware: [910B, 910C]
os: "CentOS 7.x / Ubuntu 18.04 等旧版系统"
symptom: "驱动安装过程报错 / 安装成功但 npu-smi 异常"
error: "Driver installation failed: kernel version not supported"
root_cause: |
  昇腾驱动要求内核版本 >= 4.19。旧内核缺少必要的内存管理特性。
  CentOS 7 默认内核 3.10，Ubuntu 18.04 默认内核 4.15，均不满足。
solution: |
  1. 检查内核版本：
     uname -r
     
  2. 如果低于 4.19，升级内核或换用支持的操作系统。
  
  3. 推荐操作系统（按稳定性排序）：
     - openEuler 22.03 LTS SP3（官方推荐，最稳定）
     - Ubuntu 22.04 LTS
     - Ubuntu 20.04 LTS（内核 5.4+）
     - CentOS 8（内核 4.18，勉强可用但不推荐）
     
  4. openEuler 对昇腾硬件支持最完整，多卡通信和内存管理问题最少。
verify: "uname -r 输出 >= 4.19 && npu-smi info 正常"
source: "CSDN vLLM 昇腾部署指南实测"
```

---

## 二、容器与设备挂载

### CTR-001：Docker 容器内无法访问 NPU 设备

```yaml
id: CTR-001
stage: 环境
hardware: [全部]
symptom: "容器内 npu-smi info 无输出 / 提示找不到设备"
error: "RuntimeError: Can not find available NPU device / No such file or directory: '/dev/davinci0'"
root_cause: |
  Docker 容器默认没有访问宿主设备节点的权限。
  昇腾 NPU 的设备文件（/dev/davinci*、/dev/davinci_manager 等）必须显式挂载到容器内。
solution: |
  启动容器时挂载所有 NPU 相关设备（以 8 卡为例）：
  
  docker run -itd \
    --privileged \
    --name ascend-dev \
    --net=host \
    --shm-size=1000g \
    --device=/dev/davinci0 \
    --device=/dev/davinci1 \
    --device=/dev/davinci2 \
    --device=/dev/davinci3 \
    --device=/dev/davinci4 \
    --device=/dev/davinci5 \
    --device=/dev/davinci6 \
    --device=/dev/davinci7 \
    --device=/dev/davinci_manager \
    --device=/dev/hisi_hdc \
    --device=/dev/devmm_svm \
    -v /usr/local/Ascend:/usr/local/Ascend \
    -v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi \
    your-image:tag bash
  
  关键注意事项：
  - --privileged 是必需的
  - --shm-size 至少 64g，推荐 1000g（过小会导致 IPC 队列创建失败）
  - 必须挂载 davinci_manager、hisi_hdc、devmm_svm 三个管理设备
  - /usr/local/Ascend 目录必须挂载（包含驱动和 CANN）
verify: "容器内执行 npu-smi info 显示所有卡信息"
source: "SGLang 昇腾部署实测、昇腾故障案例"
```

### CTR-002：容器内共享内存不足导致 OOM

```yaml
id: CTR-002
stage: 环境
hardware: [全部]
symptom: "大模型服务启动时直接崩溃 / IPC 相关报错"
error: "RuntimeError: unable to open shared memory object / Bus error (core dumped)"
root_cause: |
  Docker 默认共享内存只有 64MB。
  大模型推理框架（vLLM、SGLang、MindIE）使用共享内存进行进程间通信，
  64MB 远远不够，导致 IPC 队列创建失败或直接 Bus error。
solution: |
  启动容器时设置足够大的 --shm-size：
  
  docker run --shm-size=1000g ...
  
  或在已运行的容器中临时扩展（不推荐，重启后失效）：
  mount -o remount,size=100G /dev/shm
verify: "df -h /dev/shm 显示足够大的共享内存空间"
source: "CSDN SGLang 昇腾部署实测"
```

---

## 三、CUDA 迁移到 NPU

### MIG-001：代码中硬编码 .cuda() 导致报错

```yaml
id: MIG-001
stage: 迁移
hardware: [全部]
symptom: "运行模型代码时提示 CUDA 不可用"
error: "AssertionError: Torch not compiled with CUDA enabled"
root_cause: |
  模型代码或第三方库中包含 cuda 相关硬编码：
  .cuda()、.to("cuda")、torch.cuda.is_available() 等。
  在 NPU 环境中这些调用必然失败。
solution: |
  方法一：手动替换（精确控制）
  - .cuda()            → .npu()
  - .to("cuda")        → .to("npu")
  - .to("cuda:0")      → .to("npu:0")
  - torch.cuda.xxx     → torch.npu.xxx
  - CUDA_VISIBLE_DEVICES → ASCEND_RT_VISIBLE_DEVICES
  
  方法二：自动迁移（推荐，适用于 PyTorch）
  在脚本最开头添加一行：
  import torch_npu
  # torch_npu 会自动 monkey-patch 大部分 cuda API
  
  方法三：使用 torch_npu 的 transfer_to_npu 工具
  import torch_npu
  from torch_npu.contrib import transfer_to_npu
  # 自动将 .cuda() 替换为 .npu()
  
  对于第三方模型（如 HuggingFace 模型仓库中的 modeling_xxx.py）：
  需要在下载的模型文件中手动搜索替换 cuda 相关代码。
verify: "模型能在 NPU 上正常加载和执行前向传播"
source: "LLaMA-Factory NPU 文档、昇腾开源文档 FAQ"
```

### MIG-002：torch.jit 装饰器在 NPU 上不支持

```yaml
id: MIG-002
stage: 迁移
models: [ChatGLM, ChatGLM2, ChatGLM3, GLM-4]
symptom: "使用 ChatGLM 系列模型微调/训练时报错"
error: "NotImplementedError: Unknown device for graph fuser"
root_cause: |
  ChatGLM 系列模型的 modeling_chatglm.py 中使用了 @torch.jit.script
  装饰器。torch.jit 在 NPU 上不完全支持。
solution: |
  1. 找到模型目录下的 modeling_chatglm.py
  2. 注释掉所有 @torch.jit.script 装饰器
  3. 改为普通 Python 函数
  
  示例：
  # 修改前
  @torch.jit.script
  def gelu_impl(x):
      return ...
  
  # 修改后
  # @torch.jit.script  # 注释掉此行
  def gelu_impl(x):
      return ...
verify: "模型训练/推理正常启动，无 jit 相关报错"
source: "LLaMA-Factory NPU FAQ、昇腾开源文档"
```

### MIG-003：DeviceType must be NPU 但实际是 CPU

```yaml
id: MIG-003
stage: 迁移
hardware: [910B, 910C]
symptom: "模型微调时部分张量未正确迁移到 NPU"
error: "DeviceType must be NPU. Actual DeviceType is: cpu"
root_cause: |
  模型的某些子模块或数据在初始化时未正确放到 NPU 上。
  常见于自定义数据处理管道中：Dataloader 返回的 tensor 仍在 CPU。
  也可能是模型的部分层在 .npu() 时被跳过。
solution: |
  1. 确认模型完整地在 NPU 上：
     model = model.npu()
     # 验证
     for name, param in model.named_parameters():
         assert param.device.type == 'npu', f"{name} on {param.device}"
  
  2. Dataloader 中手动搬数据：
     for batch in dataloader:
         batch = {k: v.npu() for k, v in batch.items()}
  
  3. 如果使用 DeepSpeed，确认 config 中的 device 设置：
     "device": "npu"
     
  4. 检查是否有 .cpu() 的隐式调用（如 loss.item() 前不需要 .cpu()）
verify: "训练正常进行，无 DeviceType 相关报错"
source: "LLaMA-Factory NPU FAQ"
```

---

## 四、框架与依赖冲突

### DEP-001：torch / torch_npu / CANN 三方版本不匹配

```yaml
id: DEP-001
stage: 环境
hardware: [全部]
symptom: "import torch_npu 报错 / 训练时随机崩溃"
error: |
  多种表现：
  - ImportError: libhccl.so: undefined symbol: xxx
  - RuntimeError: HCCL error
  - Segmentation fault (core dumped)
root_cause: |
  torch_npu 的版本必须与 PyTorch 和 CANN 严格对应。
  三者版本不匹配是最常见的环境问题。
solution: |
  版本对应关系（截至 2026 年）：
  
  | PyTorch | torch_npu | CANN       | Python  |
  |---------|-----------|------------|---------|
  | 2.1.0   | 2.1.0     | 8.0.RC1+   | 3.8-3.10|
  | 2.2.0   | 2.2.0     | 8.0.RC3+   | 3.8-3.10|
  | 2.3.1   | 2.3.1     | 8.0.T13+   | 3.8-3.11|
  | 2.4.0   | 2.4.0     | 8.3.RC1+   | 3.8-3.11|
  | 2.5.0   | 2.5.0     | 8.3.RC1+   | 3.9-3.12|
  
  推荐安装方式（避免 pip 依赖冲突）：
  # 先安装 PyTorch（不带 CUDA）
  pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
  pip install torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu
  
  # 再安装对应版本的 torch_npu
  pip install torch_npu==2.1.0
  
  # 验证
  python -c "import torch; import torch_npu; print(torch.npu.is_available())"
verify: "python -c \"import torch_npu; print(torch.npu.is_available())\" 输出 True"
note: "详细版本矩阵见 references/version_matrix.md"
source: "知乎昇腾踩坑文章、LLaMA-Factory NPU 文档"
```

### DEP-002：辅助依赖库缺失导致隐性错误

```yaml
id: DEP-002
stage: 环境
hardware: [全部]
symptom: "训练能启动但中途报各种奇怪错误 / 某些算子 fallback 到 CPU"
error: "多种表现，不一定有明确报错，可能只是性能异常低"
root_cause: |
  CANN/torch_npu 依赖一组辅助库，pip install 时不一定会自动安装完全。
  缺失的库不一定导致直接报错，但会导致某些功能降级或隐性失败。
solution: |
  检查并安装以下依赖（使用 pip show xxx 逐一验证）：
  
  numpy>=1.19.2
  decorator>=4.4.0
  sympy>=1.5.1
  cffi>=1.12.3
  protobuf>=3.13.0
  attrs
  pyyaml
  pathlib2
  scipy
  requests
  psutil
  absl-py
  
  一键安装：
  pip install numpy decorator sympy cffi protobuf attrs pyyaml \
              pathlib2 scipy requests psutil absl-py
verify: "pip show numpy decorator sympy cffi protobuf 均有输出"
source: "知乎昇腾踩坑文章"
```

---

## 五、模型训练问题

### TRN-001：LLaMA-Factory 使用 llamafactory-cli 启动卡住

```yaml
id: TRN-001
stage: 训练
framework: LLaMA-Factory
hardware: [910B, 910C]
symptom: |
  主进程启动后卡住不动，终端无输出，各卡的训练进程不出现。
  程序完全挂起，无报错。
error: "无明确报错，程序挂起"
root_cause: |
  llamafactory-cli 在 NPU 上的进程启动机制偶发性不稳定。
  可能与 HCCL 初始化或分布式启动顺序有关。
solution: |
  不使用 llamafactory-cli，改为 torchrun 直接启动：
  
  # 将 YAML 配置改写为 shell 脚本
  FORCE_TORCHRUN=1 torchrun \
    --nproc_per_node 8 \
    --nnodes 1 \
    --node_rank 0 \
    --master_addr 127.0.0.1 \
    --master_port 29500 \
    src/train.py \
    --model_name_or_path /path/to/model \
    --dataset your_dataset \
    --output_dir ./output \
    --finetuning_type lora \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 4 \
    --learning_rate 1e-4 \
    --num_train_epochs 3
    
  如果仍使用 llamafactory-cli，确保：
  - 设置 FORCE_TORCHRUN=1
  - 更新 LLaMA-Factory 到最新版本
verify: "所有卡上出现训练进程，终端输出训练日志"
source: "知乎昇腾踩坑文章"
```

### TRN-002：DeepSpeed 单卡训练报 save_checkpoint 错误

```yaml
id: TRN-002
stage: 训练
framework: [LLaMA-Factory, DeepSpeed]
hardware: [910B]
symptom: "单卡 NPU 使用 DeepSpeed 训练时报错"
error: "AttributeError: 'GemmaForCausalLM' object has no attribute 'save_checkpoint'"
root_cause: |
  DeepSpeed 只对分布式 launcher 启动的程序中的模型用 DeepSpeedEngine 包装。
  直接用 python src/train.py 启动不会包装，因此没有 save_checkpoint 方法。
solution: |
  即使单卡也要用 torchrun 启动：
  
  torchrun --nproc_per_node 1 \
    --nnodes 1 \
    --node_rank 0 \
    --master_addr 127.0.0.1 \
    --master_port 29500 \
    src/train.py [训练参数...]
    
  或设置环境变量：
  export FORCE_TORCHRUN=1
  llamafactory-cli train your_config.yaml
verify: "训练正常完成，checkpoint 成功保存"
source: "昇腾开源文档 FAQ"
```

---

## 六、模型推理问题

### INF-001：ACL stream synchronize failed, error code:507018

```yaml
id: INF-001
stage: 推理
hardware: [910B, 910C]
symptom: "推理时报 ACL 流同步失败"
error: "RuntimeError: ACL stream synchronize failed, error code:507018"
root_cause: |
  507018 通常与推理时的随机采样策略相关。
  NPU 上的随机采样实现与 CUDA 有差异，某些情况下会触发流同步错误。
solution: |
  设置 do_sample=False，取消随机抽样：
  
  # API 调用方式
  curl http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model": "your-model",
      "messages": [{"role": "user", "content": "Hello"}],
      "do_sample": false
    }'
  
  # 代码方式
  outputs = model.generate(
      input_ids,
      do_sample=False,
      max_new_tokens=512
  )
  
  如果必须使用采样，尝试：
  - 降低 temperature（如 0.1）
  - 设置固定的 random seed
  - 升级 CANN 到最新版本（可能已修复）
verify: "推理正常完成，无 507018 报错"
source: "LLaMA-Factory NPU FAQ"
```

### INF-002：vLLM 在 NPU 上 KV Cache 分配失败

```yaml
id: INF-002
stage: 推理
framework: vLLM
hardware: [910B]
symptom: "vLLM 启动时 KV Cache 分配失败 / max-total-tokens 相关报错"
error: "RuntimeError: Failed to allocate KV cache / insufficient memory for KV cache"
root_cause: |
  SGLang/vLLM 在昇腾后端对内存分配有严格要求。
  max-total-tokens 必须大于模型的 page size，否则 KV Cache 分配会失败。
solution: |
  1. 根据模型大小调整 max-total-tokens：
     - 7B-8B 模型：--max-total-tokens 1024
     - 13B-14B 模型：--max-total-tokens 2048
     - 70B 模型：--max-total-tokens 4096
  
  2. 启动命令示例（vLLM）：
     python -m vllm.entrypoints.openai.api_server \
       --model /path/to/model \
       --device npu \
       --max-model-len 4096 \
       --block-size 128 \
       --gpu-memory-utilization 0.85
  
  3. 如果仍然 OOM，调整 mem-fraction-static：
     --mem-fraction-static 0.8  # 默认 0.9，降低给动态分配留更多空间
  
  4. Block Size 对齐（昇腾特有优化）：
     - 短文本场景：block-size=64
     - 长文本场景：block-size=128
     - 混合场景：block-size=128（推荐）
     昇腾 NPU 对内存对齐敏感，block-size 选对可提升性能 20%+
verify: "vLLM 服务正常启动，可接受推理请求"
source: "CSDN vLLM 昇腾部署指南"
```

### INF-003：NPU 显存碎片导致运行一段时间后 OOM

```yaml
id: INF-003
stage: 推理
hardware: [910B, 910C]
symptom: "服务刚启动时正常，运行几小时后开始 OOM"
error: "RuntimeError: NPU out of memory / torch.npu.memory_stats 显示高碎片率"
root_cause: |
  昇腾 NPU 对显存碎片比较敏感。Python 的垃圾回收机制在 NPU 上可能不及时。
  动态 shape 的推理请求会加剧碎片化。
solution: |
  1. 主动释放显存：在 generate 结束后显式调用：
     import torch_npu
     torch.npu.empty_cache()
     import gc
     gc.collect()
  
  2. 固定 Input Shape（最有效）：
     - 对输入进行 padding 到固定长度
     - 减少动态 shape 的变化范围
  
  3. 碎片监测：
     stats = torch.npu.memory_stats()
     print(f"碎片率: {stats.get('fragmentation', 'N/A')}")
  
  4. 定期重启推理服务（生产环境的务实方案）：
     - 设置 cron job 或 K8s 的 liveness probe
     - 在低峰期自动滚动重启
  
  5. 优化原则：环境要对齐，Shape 要固定，线程要限制
verify: "连续运行 24h+ 无 OOM"
source: "CSDN Llama 昇腾部署指南"
```

---

## 七、多卡通信（HCCL）

### HCCL-001：HCCL 初始化失败 - 上次训练进程残留

```yaml
id: HCCL-001
stage: 训练
hardware: [910B, 910C]
symptom: "启动多卡训练时 HCCL 初始化失败"
error: |
  RuntimeError: [ERROR] HCCL error in: torch_npu/csrc/distributed/ProcessGroupHCCL.cpp:64
  ERR02200 DIST call hccl api failed.
  EJ0001: Failed to initialize the HCCP process.
  Reason: Maybe the last training process is running.
root_cause: |
  上一次训练异常退出后，HCCL 进程残留未清理。
  NPU 设备被占用，新的 HCCL 初始化无法获取设备。
solution: |
  1. 杀掉残留进程：
     # 查找残留进程
     ps aux | grep -E "python|torch" | grep -v grep
     
     # 杀掉所有残留的训练进程
     pkill -9 -f "torchrun|python.*train"
     
  2. 等待 10 秒后再启动新训练：
     sleep 10
     
  3. 重置 NPU 设备（如果上述方法无效）：
     npu-smi set -t reset -i 0  # 重置第 0 张卡
     # 或重置所有卡
     for i in $(seq 0 7); do npu-smi set -t reset -i $i; done
     
  4. 确认设备已释放：
     npu-smi info  # 所有卡的 Memory Usage 应接近 0
verify: "多卡训练正常启动，所有卡参与训练"
source: "LLaMA-Factory NPU FAQ、昇腾开源文档"
```

### HCCL-002：多机训练网络配置问题

```yaml
id: HCCL-002
stage: 训练
hardware: [910B, 910C]
deployment: 多机
symptom: "多机训练时节点间通信失败"
error: "HCCL timeout / Network unreachable / Connection refused"
root_cause: |
  多机训练需要正确配置 HCCL 网络。
  NPU 使用 RoCE 网络通信，需要指定正确的网卡和端口。
solution: |
  1. 确认节点间网络连通：
     # 在各节点间互 ping
     ping <other_node_ip>
     
  2. 配置 HCCL 网络接口：
     export HCCL_IF_IP=<本机用于 HCCL 通信的 IP>
     
  3. 配置 rank table（ranktable.json）：
     {
       "server_count": "2",
       "server_list": [
         {
           "server_id": "192.168.1.1",
           "device": [
             {"device_id": "0", "device_ip": "192.168.10.1", "rank_id": "0"},
             {"device_id": "1", "device_ip": "192.168.10.2", "rank_id": "1"}
           ]
         },
         {
           "server_id": "192.168.1.2",
           "device": [
             {"device_id": "0", "device_ip": "192.168.10.3", "rank_id": "2"},
             {"device_id": "1", "device_ip": "192.168.10.4", "rank_id": "3"}
           ]
         }
       ]
     }
     
  4. 设置环境变量：
     export RANK_TABLE_FILE=/path/to/ranktable.json
     export RANK_SIZE=<总卡数>
     export RANK_ID=<当前进程的 rank>
     
  5. 防火墙检查：
     # 确保 HCCL 端口（默认 60000-60100）未被防火墙拦截
     iptables -L -n | grep 6000
verify: "多机训练正常启动，npu-smi 显示各节点的卡均在工作"
source: "CSDN 双机部署 DeepSeek-R1 指南"
```

---

## 八、显存与 OOM

### OOM-001：模型加载时即 OOM

```yaml
id: OOM-001
stage: 推理
hardware: [910B-32GB, 910B-64GB]
symptom: "模型加载阶段就报 OOM"
error: "RuntimeError: NPU out of memory. Tried to allocate X GiB"
root_cause: |
  模型参数量超过单卡显存。
  910B 有 32GB 和 64GB 两个版本，不同模型的显存需求不同。
solution: |
  显存需求估算（FP16）：
  | 模型参数量 | FP16 显存需求 | W8A8 显存需求 | 推荐卡型        |
  |-----------|-------------|-------------|---------------|
  | 7B-8B     | ~16 GB      | ~8 GB       | 910B-32GB x1  |
  | 13B-14B   | ~28 GB      | ~14 GB      | 910B-32GB x1 或 64GB x1 |
  | 34B       | ~68 GB      | ~34 GB      | 910B-64GB x2  |
  | 70B-72B   | ~140 GB     | ~70 GB      | 910B-64GB x4  |
  | 671B(MoE) | 激活~74GB   | 激活~37GB   | 910B-64GB x8+ |
  
  解决方案（按优先级）：
  1. 使用量化：W8A8 或 W4A16 可减半显存
  2. 多卡 TP 并行：--tensor-parallel-size N
  3. 如果使用 vLLM：调整 --gpu-memory-utilization 0.85
  4. 长期方案：升级到 910B-64GB 或 910C
verify: "模型成功加载到 NPU，npu-smi 显示显存使用在合理范围"
source: "CSDN vLLM 昇腾部署指南"
```

---

## 九、性能调优

### PERF-001：NPU 利用率低 / 推理速度远低于预期

```yaml
id: PERF-001
stage: 调优
hardware: [910B, 910C]
symptom: "npu-smi 显示 NPU 利用率只有 30-50%，推理速度远低于 GPU 基线"
error: "无报错，但性能不达标"
root_cause: |
  多种可能的原因：
  1. 动态 Shape 导致频繁重编译
  2. 大量算子 fallback 到 CPU
  3. 数据搬运成为瓶颈（Host-Device 传输）
  4. Block Size 未对齐 NPU 最优值
solution: |
  1. 固定 Shape（最有效）：
     - 推理时对输入 padding 到固定长度
     - 使用 torch.npu.set_compile_mode(jit_compile=False)
     
  2. 检查算子 fallback：
     # 开启算子调度日志
     export ASCEND_GLOBAL_LOG_LEVEL=1
     export ASCEND_SLOG_PRINT_TO_STDOUT=1
     # 观察是否有大量 "fallback to CPU" 的日志
     
  3. 减少 Host-Device 数据搬运：
     - 尽量在 NPU 上完成全部计算
     - 避免频繁 .cpu() 和 .npu() 的来回
     - loss.item() 会触发同步，减少调用频率
     
  4. 使用 profiler 定位瓶颈：
     with torch.npu.profile() as prof:
         output = model(input_ids)
     prof.export_chrome_trace("npu_trace.json")
     # 用 Chrome Trace Viewer 分析
     
  5. 限制 CPU 线程数（避免过度调度）：
     export OMP_NUM_THREADS=4
     export MKL_NUM_THREADS=4
     
  6. 使用 AIPP 预处理（视觉模型）：
     将图像预处理从 CPU 迁移到 NPU 的 AIPP 模块
verify: "npu-smi 显示 NPU 利用率 > 70%，推理速度达到基线 80%+"
source: "CSDN Llama 昇腾部署指南、vLLM Block Size 调优"
```

### PERF-002：vLLM Block Size 调优

```yaml
id: PERF-002
stage: 调优
framework: vLLM
hardware: [910B]
symptom: "vLLM 在 NPU 上吞吐量偏低"
error: "无报错，性能不达标"
root_cause: |
  昇腾 NPU 对内存访问对齐要求严格。
  Block Size 如果不是 NPU 缓存行的整数倍，会导致显存带宽浪费。
solution: |
  Block Size 推荐配置：
  
  | 场景         | block-size | 原因                  |
  |-------------|------------|----------------------|
  | 短文本(≤512) | 64         | 减少内存碎片            |
  | 长文本(>2K)  | 128        | 提高带宽利用率          |
  | 混合负载      | 128        | 平衡碎片和带宽          |
  | 超长文本(>8K) | 256        | 最大化连续内存分配       |
  
  高级调优参数组合（实测可提升吞吐 ~121%）：
  python -m vllm.entrypoints.openai.api_server \
    --model /path/to/model \
    --device npu \
    --block-size 128 \
    --swap-space 16 \
    --max-num-seqs 256 \
    --enable-prefix-caching \
    --gpu-memory-utilization 0.9
verify: "吞吐量测试结果明显提升"
source: "CSDN vLLM 昇腾 Block Size 调优"
```

---

## 十、模型转换（ONNX/OM）

### CVT-001：PyTorch 模型导出 ONNX 失败

```yaml
id: CVT-001
stage: 迁移
hardware: [310P, 310B]（推理卡场景）
symptom: "模型导出 ONNX 格式时报错或导出不完整"
error: "torch.onnx.export() 报 RuntimeError / 导出的 ONNX 模型验证失败"
root_cause: |
  NPU 上的某些自定义算子不在 ONNX 标准 opset 中。
  动态 shape 的导出需要特殊处理。
solution: |
  1. 在 CPU 上导出 ONNX（推荐）：
     model = model.cpu()
     dummy_input = torch.randn(1, 3, 224, 224)  # 根据模型调整
     torch.onnx.export(
         model, dummy_input, "model.onnx",
         opset_version=13,
         input_names=["input"],
         output_names=["output"],
         dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}}
     )
  
  2. 验证 ONNX 模型：
     import onnx
     model = onnx.load("model.onnx")
     onnx.checker.check_model(model)
  
  3. 使用 ATC 工具转为 OM 格式（昇腾离线推理）：
     atc --model=model.onnx \
         --framework=5 \
         --output=model \
         --soc_version=Ascend910B \
         --input_format=NCHW \
         --input_shape="input:1,3,224,224"
verify: "OM 模型文件生成成功，可用 pyACL 加载推理"
source: "CSDN PyTorch 到 OM 转换指南"
```

---

## 十一、特定框架适配

### FW-001：SGLang + 昇腾 triton-ascend 报错

```yaml
id: FW-001
stage: 推理
framework: SGLang
hardware: [910B]
cann: "8.3.RC1+"
symptom: "SGLang 启动时 triton 相关模块报错"
error: "ImportError 或 AttributeError 关于 triton 错误类"
root_cause: |
  triton-ascend 重新组织了错误类的命名空间，与标准 triton 不同。
  需要使用昇腾社区适配的 triton-ascend 版本。
solution: |
  安装昇腾适配的 triton：
  pip install triton-ascend
  
  如果仍有导入错误，检查是否同时安装了标准 triton：
  pip uninstall triton
  pip install triton-ascend
verify: "SGLang 服务正常启动"
source: "CSDN SGLang 昇腾部署实测"
```

### FW-002：InternVL2 在 NPU 上训练速度异常慢

```yaml
id: FW-002
stage: 训练
framework: InternVL2
hardware: [910B]
symptom: |
  InternVL2-8B 训练 16h，同数据量 Qwen2-VL-7B 只需 6.5h。
  速度差距达 2.5 倍。
error: "无报错，但速度异常"
root_cause: |
  InternVL2 开发者明确表示不会主动进行 NPU 适配。
  模型中可能有大量算子 fallback 到 CPU 执行。
  视觉编码器部分的某些操作在 NPU 上未优化。
solution: |
  1. 检查算子 fallback 情况（见 PERF-001）
  2. 对 modeling 代码做针对性优化：
     - 替换不支持的算子为 NPU 支持的等价实现
     - 对视觉编码器使用 torch.npu.amp 混合精度
  3. 考虑替换为 NPU 适配更好的模型：
     - Qwen2-VL（LLaMA-Factory 原生支持 NPU）
     - 使用 LLaMA-Factory 框架而非 InternVL2 原生训练脚本
  4. 若必须使用 InternVL2：
     - 使用 LLaMA-Factory 加载并训练（适配更好）
     - 关闭 torch.jit 相关功能
     - 设置 OMP_NUM_THREADS=4
verify: "训练速度提升到可接受范围（与 GPU 差距 < 50%）"
source: "知乎昇腾踩坑文章、GitHub InternVL2 issue"
```

### FW-003：MindIE 多机部署 DeepSeek-R1 集群配置

```yaml
id: FW-003
stage: 推理
framework: MindIE
hardware: [910B]
deployment: 多机
symptom: "双机部署 DeepSeek-R1 W8A8 量化模型时配置复杂"
error: "多种配置相关错误"
root_cause: "多机部署需要正确配置 NPU 网络、容器环境和 MindIE 参数"
solution: |
  完整部署流程：
  
  1. 每台机器安装驱动和 CANN（见 ENV-001）
  
  2. 配置 NPU 网络（每台机器执行）：
     # 查看 NPU 网卡
     hccn_tool -i 0 -ip -s address 192.168.10.1 255.255.255.0
     hccn_tool -i 1 -ip -s address 192.168.10.2 255.255.255.0
     # ... 为每张卡配置 IP
  
  3. 配置 ranktable.json（见 HCCL-002）
  
  4. Docker 容器启动（见 CTR-001）
  
  5. MindIE 服务配置（config.json）：
     {
       "model_name": "DeepSeek-R1",
       "model_path": "/path/to/model",
       "tensor_parallel_size": 16,  # 双机各 8 卡
       "quantization": "w8a8",
       "max_batch_size": 32,
       "max_seq_len": 8192
     }
  
  6. 启动服务：
     # 机器1
     RANK_TABLE_FILE=ranktable.json RANK_SIZE=16 RANK_ID=0 \
       mindie-service start --config config.json
     
     # 机器2
     RANK_TABLE_FILE=ranktable.json RANK_SIZE=16 RANK_ID=8 \
       mindie-service start --config config.json
verify: "API 请求正常返回推理结果"
source: "CSDN 双机部署 DeepSeek-R1 指南"
```
