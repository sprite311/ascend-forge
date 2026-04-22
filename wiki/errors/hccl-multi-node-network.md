---
id: hccl-multi-node-network
title: HCCL 多机训练网络配置问题
kind: error
signature: "HCCL timeout / Network unreachable / Connection refused"
aliases: ["HCCL-002", "hccl-multi-node", "ranktable", "RoCE", "multi-node-train"]
tags: [training, hccl, distributed, multi-node, network, ranktable, roce]
related: [910b, 910c, mindformers, torch-npu]
stage: 训练
hardware: [910B, 910C]
status: stable
last_verified: 2026-04-20
sources:
  - skill/ascend-troubleshoot/references/knowledge_base.md#HCCL-002
---

# HCCL 多机训练网络配置问题

## 症状
多机训练启动时 HCCL 超时 / 连接拒绝 / 网络不可达；单机内部没问题，但一加第二台就卡 `init_process_group`。

## 报错示例

```
HCCL timeout
Network unreachable
Connection refused
```

## 根因
昇腾多机训练走 **RoCE**（RDMA over Converged Ethernet）网络；需要：
1. 节点间 IP 互通（管理网）
2. 每张卡的 **device_ip** 配置正确（ranktable.json）
3. `HCCL_IF_IP` 指定本机用于 HCCL 的网卡 IP
4. 防火墙放行 HCCL 端口（默认 60000–60100）

任何一条漏配都会表现为以上错误。

## 修复

### Step 1｜确认管理网连通
```bash
# 在每台节点
ping <other_node_ip>
```

### Step 2｜设置 HCCL 网卡 IP
```bash
export HCCL_IF_IP=<本机用于 HCCL 通信的 IP>
```

### Step 3｜写 ranktable.json（2 机 × 2 卡示例）

```json
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
```

### Step 4｜设置环境变量
```bash
export RANK_TABLE_FILE=/path/to/ranktable.json
export RANK_SIZE=<总卡数>
export RANK_ID=<当前进程的 rank>
```

### Step 5｜防火墙
```bash
# 确保 HCCL 端口段（60000–60100）未被拦截
iptables -L -n | grep -E '6000[0-9]|6010[0-9]'
# 必要时放行
# iptables -I INPUT -p tcp --dport 60000:60100 -j ACCEPT
```

## 验证
```bash
# 两机 npu-smi 都显示卡在工作；rank 0 - N 全在日志里
npu-smi info -t usages
```

## 相关
- 单机残留进程导致的 HCCL 初始化失败：[`wiki/errors/hccl-residual-process.md`](hccl-residual-process.md)
- Playbook：[`wiki/playbooks/general-debug.md`](../playbooks/general-debug.md)

## Backlinks
<!-- auto -->
_无反链。_

## Changelog
- 2026-04-20: 迁入 from knowledge_base.md#HCCL-002. source: case/2026-04-20-troubleshoot-migration-wave1
