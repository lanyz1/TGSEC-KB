# nginx 前置页替换框架 404 —— 怎么不把它读成「WAF 拦截」

## 案例（FastAdmin / ThinkPHP 5.0.28，2026-10）

环境：`nginx 1.30.4` + PHP-FPM + ThinkPHP **5.0.28** + FastAdmin，单入口 `public/index.php`，`app_debug=1`。
docroot `/www/wwwroot/<site>/public`，应用在 `public/../application/`（调试页自己吐出来的路径）。

### 症状
这一批请求**全部返回同一个 146 字节 nginx 404 页**：

| 请求 | 返回 |
|---|---|
| `?s=/admin/index/login` | 146B nginx 404 |
| `?s=/api/common/upload` | 146B nginx 404 |
| `?s=/index/\think\app/invokefunction&function=phpinfo&vars[0]=1` | 146B nginx 404 |
| `?s=/index/zzz_noexist/zzz` | 146B nginx 404 |
| `?s=/index/index/index` | **302**（正常进框架） |

**当时的误判**：结论写成「nginx 对 `?s=` 里的 `admin`/`api`/`think` 做关键词拦截」。

### 三个证伪实验（把假设打死）
1. **关键词放到框架会忽略的位置 ⇒ 放行**
   - `?s=/index/ajax/lang/ZZZ/AAA` → 200（TP 忽略多余路径段）
   - `?s=/index/ajax/lang/admin` → **200**
   ⇒ 若 nginx 对 `s` 做「包含 admin 即拦」，这条必 404。
2. **关键词放到别的参数 ⇒ 放行**
   - `?s=/index/ajax/lang&controllername=admin` → **200**
   ⇒ 过滤器（若有）只作用于 `s`，不作用于整个 query。
3. **URL 编码**
   - `?s=/%61dmin` → 404；`?s=/inde%78/index/index` → 302
   ⇒ 要成立必须是「decode 后再匹配」，与「nginx 不 decode 所以编码可绕」自相矛盾。

### 决定性判据：500 是否原样透出
- `GET /index/ajax/upload` → **HTTP 500 + 约 34KB ThinkPHP 调试页**（完整堆栈、env、绝对路径）—— **原样返回，没被替换**。
- 框架产生的 404 → **统一变成 146B nginx 页**。

⇒ nginx 只替换 **404**，没替换 500。**说明那些 404 是框架自己产生的**，
nginx 只是用 `error_page` / `fastcgi_intercept_errors` 把正文换成了自己的默认页。**根本没有 WAF。**

### 正确模型
`application/` 下三件事都产生框架 404，而它们在外部长得**一模一样**：
- `common`、`admin` 在 FastAdmin 的 `deny_module_list` 里 → 框架抛 404
- `api` 目录被删（`/index/ajax/upload` 里 `action('api/common/upload')` 抛 `ClassNotFoundException: app\api\controller\Common`）→ 框架抛 404
- 控制器不存在（`/index/zzz_noexist/zzz`）→ 框架抛 404

## 可复用的判据与操作

1. **看到「一页通用 nginx 404」时，先别叫 WAF。** 做 500 探针：主动让应用抛 500（类型错误、不存在的类）。
   **500 原样返回 ⇒ nginx 只换 404 ⇒ 那些 404 是框架级的。**
2. **多余路径段探针**：`?s=<已知可用路由>/<垃圾>/<垃圾>` 仍 200 ⇒ 框架忽略多余段。
   这同时是「我有没有进到框架」的廉价 oracle。
3. **被换页的 404 正文读不到** ⇒ 无法用 404 正文区分「模块被拒」与「模块不存在」。
   要区分就换**副作用通道**：FastAdmin 的 `/index/ajax/lang?controllername=<模块>` 只在**该模块目录存在**时才返回该模块语言包
   （拿 md5 与默认包比）。`controllername=admin` 无变化 ⇒ admin 模块目录不存在。
4. **主动造 500 换信息**：数组参数打公开端点（`?param[]=x`）→ 框架 `InvalidArgumentException`，
   调试页吐出**应用侧调用点 `文件:行号`** 与整套 env/常量 —— 这是被换页的 404 给不了的。
5. 「路由枚举命中数少」**不等于**「隐藏路由少」：被 deny 的模块与被删的目录都伪装成同一个 404。
   把路由枚举结论降级为「我这份字典没命中」。
6. **存在性 302 也无法枚举 action**：FastAdmin 的 `Frontend::_initialize()` 在 action 解析**之前**就
   重定向登录，所以「302」既可能是「action 存在但需登录」也可能是「action 不存在」；
   用 `?param[]=x` 造 500 也会对**不存在**的 action 照样 500（`_initialize` 更早触发）。
   ⇒ 在这类目标上**放弃 action 全量枚举**，改从**前端 JS / 注释**里挖真实 action 名。

## 反例备忘（别浪费时间）
- `\think\app/invokefunction`、`_method=__construct` 在 TP **5.0.28 已修复**（5.0.24 起加控制器名过滤）。
  编码（`%5C`）、PATH_INFO、大小写变体都不行。指纹到 `THINK_VERSION 5.0.28` 就别再打。
- FastAdmin `lang` LFI（CVE-2024-7928）payload **不带扩展名**（`lang=../../application/database`），
  代码自己会拼 `.php`；带扩展名的写法（`…/etc/passwd` → `passwd.php`）永远打不中。
