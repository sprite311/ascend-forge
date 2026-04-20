# cases/

每次非闲聊任务结束由 `knowledge-curator` 产出一份归档。

- 命名：`YYYY-MM-DD-<kebab-slug>.md`
- schema：见 [`docs/KNOWLEDGE-MODEL.md §5`](../docs/KNOWLEDGE-MODEL.md)
- 索引：`cases/INDEX.jsonl`（每行一个 case 的 frontmatter 精要，由 consolidation 重建）

## 为什么每次都记录？

因为：

1. 知识的"来源"必须可回溯。memory / wiki / rule 的每一条都要能指回某个 case。
2. RAG 召回依赖案例多样性。
3. 用户审阅进化时，看 case 比看零散 memory 更直观。

## 归档 vs 保留

- 默认永不自动删；
- `case_retention_days`（见 `.agent/config.yaml`）超期后 consolidation 可给 `archived: true` 标签，仍保留文件。
