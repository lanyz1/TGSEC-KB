# ThinkPHP 6 trace page — field notes

Observed on a TP 6.1.x admin/agent API (`app/adminapi`, `app/agentapi`, `app/channelapi`
application layout, CRMEB-derived) behind nginx. Everything below was recovered without a shell.

## Forcing the page

The default API response is `{"code":1055,"msg":"..."}` baked by
`app\adminapi\exception\AdminApiExceptionHandle` → `app('json')->create(...)` →
`think\Lang::get($msg, [], $range)`. Two ways to get the verbose page instead:

1. Send `Accept: text/html` on the same failing request.
2. Make the handler itself throw (a type error on a parameter it does not expect) — the uncaught
   `Throwable` falls through to the framework handler and renders the trace.

## What the tabs give you

| Tab | Value |
|---|---|
| 基本 (Base) | request method/URL/params, framework version, loaded file list |
| 文件 (File) | source window around the throwing line |
| 流程 (Flow) | `data.file` + `data.line` per frame — the line-number oracle source |
| SQL | every executed statement + bindings (schema extraction + parameterization proof) |
| 调试 (Debug) | `$_SERVER`, session, cookies, env |

Harvest targets inside the JSON payload the page embeds: `data.file`, `data.line`, `trace`, and
the SQL list.

## Schema extraction

The SQL tab shows `SELECT column_name, data_type ... FROM information_schema.columns
WHERE t.table_name = 'game_user'` — the *statement* is shown, not the result, so read the column
list out of the application's own `SELECT` statements instead. From a login statement the full
column set came out as:

`[id],[username],[password],[salt],[mobile],[status],[last_login_time],[last_login_ip],[google_verify],[PackID]`

plus sibling tables (`game_agent_account`, `T_PackageUrl`, `T_PackageConfig`) from other queries,
and the DSN `sqlsrv:Database=<db>;Server=<ip>,1433` from a DB-layer trace frame. `google_verify`
in the schema is the tell that 2FA exists and that its secret lives in that row.

## Line-number oracle (worked example)

Login for `admin` and for arbitrary names returned the identical message. The ONLY difference was
the leaked line:

- `SystemAdminServices.php:600` → user does not exist
- `SystemAdminServices.php:612` → password mismatch

Result: `admin` alone existed in the backend user table; 45+ candidate names all hit 600. Also
found: `<=120` chars reached 612, `>=126` chars tripped a length wall at 608. The throwing frame
was `SystemAdminServices.php:564` → `checkUser()` → `throw` at 612, leaving a bounded source gap.

## Source windows

Two complementary leak shapes:

1. **File tab window** — an HTML fragment with `<ol start=NNN>` / `line-0-NNN` anchors giving ~30
   lines around the throwing line. Slide it by changing which branch throws.
2. **Re-declaration fatal** — including a file whose class/function is already loaded prints the
   symbol body: `Cannot declare class ..., because the name is already in use`, then the source.
   This recovered middleware (`BasicMiddleware.php`), `Json.php`, `AdminApiExceptionHandle.php`,
   `PackageLogic`, the `MasterDb`/`BaseDb` DSN wrapper, and `think\Lang` itself.

Stitch windows by line number; a thin band (e.g. 564–610) stays missing until a branch is found
that executes *inside* it.

## lang-param LFI chain

```
body param  lang=<relative path>
  -> Lang::get($msg, [], $request->lang)      # 3rd arg = range
  -> switchLangSet($range)
  -> include $range                            # arbitrary local include
```

- The **query-string** `lang` is stripped by the URL `detect()` filter; the **body** `lang=`
  reaches the third argument. A `think_lang` cookie is also honoured — a second carrier worth
  testing because it may bypass the query filter.
- The include is silent: values surface only when the exception message equals a key in the loaded
  array. Proven by pointing at a real language pack, then aiming at `../../../../config/database.php`
  (loaded, but its keys are `connections`/`hostname`, not the exception message — so the include
  happens while the data stays hidden).
- Depth calibration and `open_basedir` (`<webroot>:/tmp`) bound the reachable set.
- Dotted lookup (splitting on `.`) is the theoretical way to read `connections.default.password`
  from a loaded config array — it only pays off if a code path throws a message you control and
  that starts with a config key. Look for request-derived exception messages before investing more.

## Walls to expect

- `BasicMiddleware` may enforce **both** a request signature and an Origin allowlist; passing the
  signature still yields `无法识别请求来源` when the Origin is not registered.
- Route names guessed from an admin/agent SPA are frequently absent on the API app: a signed
  request to a nonexistent controller returns **404**, while a real-but-unauthorized one returns an
  auth error. Distinguish them before concluding "the signature bypass failed".
- A dev-environment app (`projectName: "brldev"`) can have fully working endpoints that return
  empty data — a dead end that looks like progress. Check the data exists before building on it.
