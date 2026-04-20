# Adapter · openclaw

> openclaw 的具体规范会随版本演进。本 adapter 给出"可工作"基线 + 工具映射表，需按所用版本校准。

## 运行原理

1. openclaw 以 `AGENTS.md` 为入口。
2. `agents/*.md` 的 frontmatter + prompt 被作为 persona / role 加载。
3. 工具调用走 openclaw 本身的 runtime（shell / file / MCP 等），子 agent 能力通过 prompt chain 实现。

## 工具能力映射

| 抽象能力 | openclaw 工具（示意，按版本核实） |
|---|---|
| shell | `shell` / `run` |
| read_file | `read_file` / `fs.read` |
| write_file | `write_file` / `fs.write` |
| edit_file | `edit` / `patch` |
| list_files | `list_dir` / `glob` |
| search | `grep` |

> 请在 `adapters/openclaw/tools.md` 里维护本环境下的实际工具名；subagent prompt 里统一用**能力名**，由此表翻译。

## 子 agent 的降级

如果所用 openclaw 版本尚不支持真子 agent（只能单主 agent 多工具），就让主 agent "扮演"不同角色——在需要时把对应 `agents/<name>.md` 作为段内 persona 插入 system prompt。

## 设置建议

- 在 openclaw 的 settings 里配白名单 / 黑名单（对应 `.agent/config.yaml` 的 `safety.dangerous_command_patterns`）。
- 为本项目 repo 授予读写权限（仅限于 `.agent/config.yaml` 的 `write_whitelist`）。

## 自检

同 `adapters/claude-code/README.md` 的"运行自检"段。
