---
name: sqlite-353-vuln-matrix
description: "Use when 目标带 SQLite 3.53.4 组件或 CLI/扩展面：14 条本地溢出、鉴权旁路、CLI 命令注入、sqlite3_rsync RCE。"
---

# SQLite 3.53.4 漏洞矩阵（14 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 SQLite 3.53.4 上一次性产出 14 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `sqlite-cli-go` | High | Local | Command injection | go and slash terminators then dot-command |
| `sqlite-cli-recover` | High | Local | Command injection | recover dump emits hostile schema as dot-command |
| `sqlite-collate-depth` | High | Local | Crash | COLLATE chain skips SQLITE_LIMIT_EXPR_DEPTH |
| `sqlite-cte-nest` | High | Local | Crash | nested CTEs skip nNestSel view-depth cap |
| `sqlite-fj-using-auth` | High | Local | Privilege leftover | FULL JOIN USING skips sqlite3AuthRead |
| `sqlite-fts3-snippet` | High | Local | UAF | FTS3 snippet vs fts3EvalRestart |
| `sqlite-fts5-rowidmerge` | High | Local | Crash | FTS5 detail=none prefix-merge under-alloc |
| `sqlite-fts5-securedel` | High | Local | Crash | FTS5 secure-delete PutVarint footer overrun |
| `sqlite-rsync-ssh` | High | Remote | RCE | SSH filename command injection |
| `sqlite-rtree-rowid0` | High | Local | UAF | rtree last_insert_rowid 0 node hash |
| `sqlite-session-ncol` | High | Local | heap OOB write | session changeset same-name nCol growth |
| `sqlite-values-union` | High | Local | Crash | VALUES UNION ALL fallback cleanup stack overflow |
| `sqlite-wal-pagesize` | High | Local | Info leak | WAL/DB page-size mismatch uninitialized page tail |
| `sqlite-xfer-auth` | High | Local | Privilege leftover | INSERT SELECT xfer skips source READ |

## 逐条要点（Class/Reach 原文摘录）
### `sqlite-cli-go`
  - **Class:** Command injection
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c`) default `sqlite3` CLI still treats SQL Server `go` and Oracle `/` as statement terminators. `line_is_command_terminator` rewrites that line to `;`. The next line with an 
### `sqlite-cli-recover`
  - **Class:** Command injection
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c`) CLI `.recover` prints hostile `sqlite_schema.sql` as a later dot-command. `recoverOneStmt` prepares only the first statement. A planted `CREATE TABLE` plus newline `.shel
### `sqlite-collate-depth`
  - **Class:** Crash
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c14082339b66c7b7158d609a771e64ca69`, SOURCE_ID `2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc`) - Hwaci
### `sqlite-cte-nest`
  - **Class:** Crash
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c14082339b66c7b7158d609a771e64ca69`, SOURCE_ID `2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc`) - Hwaci
### `sqlite-fj-using-auth`
  - **Class:** Privilege leftover
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c` / SOURCE_ID `2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc`) - Hwaci
### `sqlite-fts3-snippet`
  - **Class:** UAF
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c14082339b66c7b7158d609a771e64ca69`, SOURCE_ID `2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc`) - Hwaci
### `sqlite-fts5-rowidmerge`
  - **Class:** Crash
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c`, SOURCE_ID `2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc`) FTS5 `detail=none` prefix merge under-allocates the output buffer in `ft
### `sqlite-fts5-securedel`
  - **Class:** Crash
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c14082339b66c7b7158d609a771e64ca69`) - Hwaci
### `sqlite-rsync-ssh`
  - **Class:** RCE (command injection)
  - **Reach:** Remote (UI:R)
  - **SQLite** 3.53.4 (`b09c88c`) `sqlite3_rsync` quotes `USER@HOST:PATH` for local `/bin/sh -c`. OpenSSH then space-joins the remote argv for the login shell without those quotes. A semicolon, `$()`, bac
### `sqlite-rtree-rowid0`
  - **Class:** UAF
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c14082339b66c7b7158d609a771e64ca69`, SOURCE_ID `2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc`) - Hwaci
### `sqlite-session-ncol`
  - **Class:** heap OOB write
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c14082339b66c7b7158d609a771e64ca69`, SOURCE_ID `2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc`) with `-DSQLITE_ENABLE_SESSION`. A two-b
### `sqlite-values-union`
  - **Class:** Crash
  - **Reach:** Local
### `sqlite-wal-pagesize`
  - **Class:** Info leak
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c`) still short-reads a WAL frame into a full pager page with no tail memset. `walIndexRecover` accepts any power-of-two WAL page size in `[512, SQLITE_MAX_PAGE_SIZE]` and ne
### `sqlite-xfer-auth`
  - **Class:** Privilege leftover
  - **Reach:** Local
  - **SQLite** 3.53.4 (`b09c88c`, SOURCE_ID `2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc`) still takes the `xferOptimization` fast path for `INSERT INTO dest SELEC

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
