# tools/

离线工具集。跟 Agent 运行时解耦——可以人手跑、也可以用 cron / CI / `/consolidate` 触发。

| 文件 | 作用 |
|---|---|
| `evolve.py` | Consolidation 流水线（去重 / GC / 索引重建 / 冲突报告）。当前为 stub。 |
| `wiki_link_check.py` | 维护 wiki 的 `related:` 双向链接 + `## Backlinks`。 |
| `rag_index.py` | 给 `cases/` 建检索索引（BM25 或向量）。 |

所有脚本都**只写 `.agent/config.yaml` 白名单内路径**，并保持幂等。

## 建议

- `pip install --break-system-packages pyyaml` 等依赖按需
- 跑之前先 `git status` 确认干净；脚本应在自己的工作分支上跑
- 出错要退避，不要半写半改
