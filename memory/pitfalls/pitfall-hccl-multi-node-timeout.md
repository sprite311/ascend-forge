---
id: pitfall-hccl-multi-node-timeout
date: 2026-04-22
tags: [hccl, multi-node, timeout, ranktable, rocev2, network, ascend]
status: active
source: training-knowledge-cutoff-2025-05
ttl_days: 365
verified_at: 2026-04-22
---

# Pitfall：多机 HCCL 起不来 / 训练到第 N 步卡住

## 现象（典型三连）

```
[ERROR] HCCL: Network unreachable, check RoCE config
[ERROR] HCCL: ranktable.json parse failed
[ERROR] HCCL: collective timeout after 600s, rank 3 not responding
```

或者更隐蔽：**前 100 step 正常，第 101 step allreduce 卡 600s 超时**。

## 根因矩阵

| 症状 | 大概率根因 |
|---|---|
| 起服务瞬间报 Network unreachable | RoCE 网卡 / `HCCL_SOCKET_IFNAME` 错了 |
| `ranktable parse failed` | json 里 `server_id` / `device_id` 字段不对；或注释残留（json 不支持） |
| 前面 OK，中途超时 | 某张卡实际挂了；或 MTU / flow control 配置不对导致 packet drop |
| 只有 inter-node allreduce 慢，intra-node 正常 | RoCE v2 PFC 没配；或走了 TCP fallback |
| 训练无 warning 但 loss 间歇跳 | gradient allreduce 中有 NaN/Inf 没 abort（bf16 + bad init 常见）|

## 排查 checklist（按顺序跑）

### 1. 物理 / 内核层

```bash
# 看 RoCE 网卡 up
ip -br link | grep -E "enp|ib"
# 看 MTU（建议 4200 用于 RoCE，不能和 PFC 配置冲突）
ip link show enp189s0f0 | grep mtu
# 看 ECN / PFC（需和交换机商量好）
ethtool --show-priv-flags enp189s0f0 | grep -i pfc
```

### 2. 昇腾层 — `hccn_tool`

```bash
# 检查所有 8 张卡的 RoCE 网口状态
for i in 0 1 2 3 4 5 6 7; do
  hccn_tool -i $i -link -g                  # up/down
  hccn_tool -i $i -ip -g                    # IP 是否分配
  hccn_tool -i $i -net_health -g            # 自检
done

# 节点间 ping（测 NPU 到 NPU）
hccn_tool -i 0 -ping -g address=<peer_npu_ip>
```

**红线**：`net_health -g` 不是 Success → 物理链路有问题，别再调软件。

### 3. `ranktable.json` 校验

必须项（示意）：
```json
{
  "version": "1.0",
  "server_count": "2",
  "server_list": [
    {
      "server_id": "192.168.1.10",
      "device": [
        {"device_id": "0", "device_ip": "29.0.0.1", "rank_id": "0"},
        {"device_id": "1", "device_ip": "29.0.0.2", "rank_id": "1"}
      ]
    }
  ],
  "status": "completed"
}
```

常见错：
- **json 写了注释** → 用 `python -c "import json; json.load(open('ranktable.json'))"` 先校验
- `server_id` 用了主机名而非 IP → 部分 HCCL 版本解析不了
- `device_ip` 是 NPU 自己的 RoCE IP（`hccn_tool -i 0 -ip -g`），**不是主机 IP**

### 4. 环境变量三件套

```bash
export HCCL_SOCKET_IFNAME=enp189s0f0     # 首轮握手走的以太网接口
export HCCL_CONNECT_TIMEOUT=600          # 默认 120s 对大集群太短
export HCCL_EXEC_TIMEOUT=1800            # 集合通信执行超时
# 可选 debug
export HCCL_DEBUG=INFO                   # 打详细日志
export ASCEND_GLOBAL_LOG_LEVEL=1         # CANN 日志 info
```

### 5. 启动脚本顺序

- **master 先起，再起 workers**（反了容易卡 rendezvous）
- 多机启动前 `pkill -9 python`，清残留进程（见 [hccl-residual-process](../../wiki/errors/hccl-residual-process.md)）
- 用 msrun / torchrun 时确认 `--nnodes` / `--master_addr` / `--master_port` 正确

## "第 N 步才挂"的特殊排查

如果前 N 步正常：

1. **不是通信配置**（配错从 step 0 就挂）
2. 大概率是 **某张卡 OOM / gradient overflow / NaN**
3. 看 `/var/log/npu_xxx.log` 里有没有 `aicore exception` / `ECC error`
4. 降 batch / 降 seq / 打开 `loss_scale` 动态缩放重试
5. 如果是 **bf16 训练**：在 optimizer step 前加 `torch.isfinite(loss).all()` 检查，不是 all finite 就 skip 这步

## 为什么这个坑特别贵

- **每次 debug 循环 20-30 min**（要起 2+ 机、等 rendezvous、等 timeout）
- 错误信息往往在 rank 0 以外的机器上，**rank 0 的 log 只说 "timeout"，没根因**
- 多机环境不是"我本机测一下"能复现的——**必须在目标集群里调**

## 缓解：三个"提前做"

1. **首次上多机，先跑 `hccn_tool -i 0 -link_stat`**，确认物理健康才走软件路径
2. **ranktable 用脚本生成，不要手写**（见 `skills/ascend-ranktable-gen/`）
3. **加 heartbeat**：训练每 100 step 打一行 `[rank R] alive at step N`，卡的那一刻能立即看是谁挂了

## 相关

- `wiki/errors/hccl-multi-node-network.md`
- `wiki/errors/hccl-residual-process.md`
- `wiki/hardware/910b.md`
- `memory/facts/fact-ascend-hardware-specs.md`
