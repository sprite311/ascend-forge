# openclaw 工具能力映射表

> 由接入者按所用 openclaw 版本实际填写。subagent prompt 中统一用**能力名**，
> 主 agent / adapter 按此表翻译成实际工具调用。

| 能力 | 工具名 | 示例 |
|---|---|---|
| shell | `TBD` | `TBD` |
| read_file | `TBD` | `TBD` |
| write_file | `TBD` | `TBD` |
| edit_file | `TBD` | `TBD` |
| list_files | `TBD` | `TBD` |
| search | `TBD` | `TBD` |
| subagent_invoke | `TBD` 或降级到 prompt chain | `TBD` |

## 特殊情况

- 如果 openclaw 支持 MCP：可把昇腾 `npu-smi` 等包成 MCP server，工具名写在此。
- 如果需要 sandbox 网络访问：在此说明 allowlist 域名。
