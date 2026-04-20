# wiki/playbooks/

每页一个**端到端场景剧本**。比如"在 910B×8 上首次上线 Qwen2-72B"、"遇到性能回归的排查流程"。

## 模板
```markdown
---
id: first-deploy-72b-on-910b
title: 在 910B×8 上首次部署 72B 模型
kind: playbook
tags: [deployment, 910b, 72b]
related: [mindie, flash-attention, qwen2-72b]
status: stable
last_verified: YYYY-MM-DD
---

## 场景
## 前置清单
## 步骤（映射到 skills）
  1. [env-doctor checklist](../../agents/ascend-env-doctor.md)
  2. [model-adaptation](../../skills/model-adaptation/SKILL.md)
  3. [mindie-deployment](../../skills/mindie-deployment/SKILL.md)
  4. [benchmark-baseline](../../skills/benchmark-baseline/SKILL.md)
## 验证
## 常见坑
## Changelog
```
