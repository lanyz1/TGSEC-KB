# 会话历史检索（"这需求历史上提过吗 / 我承诺过吗"）

用途：判定某个需求/功能名是不是用户真的提过、或我是否承诺过，抗「压缩记忆缺失」与「凭印象答」。

## 定位会话库
- Hermes 会话库在 profile 目录下：先 `find <profile_dir> -maxdepth 2 -name '*.db' -o -name '*.sqlite*'`，常见为 `state.db`（可达数百 MB）。
- 只读打开，绝不动原库：`sqlite3.connect("file:<path>?mode=ro", uri=True)`。

## 中文检索的关键坑
- **主全文索引对 CJK 长串无效**：它把整段中文当一个 token，搜「单项目导入」这种多字组合命中不到。
- **改用 trigram 变体表**（`sqlite_master` 里 `name LIKE '%fts%'` 通常能看到 `messages_fts_trigram`），它支持中文子串检索。
- `LIKE '%词%'` 作兜底（覆盖 trigram 未索引的短词/符号）。

## 查询纪律
- 先看 schema：`PRAGMA table_info(messages)` + 列 `sqlite_master`，别猜列名。表名/列名（role / session / 时间列）以实际 schema 为准。
- **按 role 分开统计**：`user` 命中 = 用户真提过；`assistant` 命中 = 单方自述，且**必须排除当前会话**，否则本次取证片段会污染结论。
- 输出：按时间倒序、限条数、每条打 时间 + session_id + 关键词前后 ~200 字窗口。
- 用会话库回答「提过吗」时，永远同时报两个集合：user 命中数 / assistant 命中数（附排除条件）。

## 结论写法
- 「user 角色历史上 0 次提到 X」⇒ 可判定这不是「做过忘了」，而是从未提出。
- 命中全落在别的项目会话里（跨项目同名工具/词）时，要按 session 归类后再说，别把别案的历史当成本案需求。
