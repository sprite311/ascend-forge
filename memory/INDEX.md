# Memory Index

> 由 `knowledge-curator` 维护。每次 consolidation 重建。
> 只放索引项（id、tags、一句话摘要、source）；详细内容在对应 md 文件。

---

## Facts (`facts/`)
<!-- id | tags | summary | source -->
_暂无条目。首次任务后会自动出现。_

## Lessons (`lessons/`)
_暂无条目。_

## Pitfalls (`pitfalls/`)
_暂无条目。_

## Preferences (`preferences/`)
_暂无条目。_

---

## 维护约定

- 新增条目时在对应小节**追加一行**，模板如下（`KIND` 为 `facts` / `lessons` / `pitfalls` / `preferences` 之一；`ID` 为条目的 kebab-id）：

  ```
  - `ID` → `KIND/ID.md` — `[tag1, tag2]` — 一句话摘要 — src: `case/…` 或 `user-confirmed`
  ```

  实际条目用 Markdown 链接指向真实文件。示例（只在 preferences/ 下存在 pref-quant-w8a8.md 时才应出现）：

  ```
  - [pref-quant-w8a8](preferences/pref-quant-w8a8.md) — [quantization, inference] — 偏好 W8A8 — src: case/2026-04-20-xxx
  ```
- 过期（超过 `ttl_days` 未 reverify）条目前面加 `⚠️`。
- 被取代的条目移到 [`archive/`](#archive) 小节（独立 `archive/` 目录可选）。
- 单文件行数 > 300 建议拆分主题子索引。

## Archive
_无_
