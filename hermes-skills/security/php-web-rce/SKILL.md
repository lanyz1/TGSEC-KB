---
name: php-web-rce
description: Use when testing PHP/Laravel apps for RCE or file read.
---

# PHP Web RCE — 攻击手册

## 触发条件

在以下场景加载本技能：
- 目标是 PHP / Laravel / Symfony / ThinkPHP 等 Web 应用，需要 RCE 或任意文件读取
- 侦察发现调试组件、文件操作 sink、反序列化 sink
- 发现 Laravel Ignition（`/_ignition/health-check`）、LFI、`phar://` 用法、debug 模式开启

---

## 1. Laravel Ignition RCE — CVE-2021-3129

### 1.1 检测（一条命令确认）

```bash
curl -s "https://TARGET/_ignition/health-check"
# 返回 {"can_execute_commands":true} → 漏洞存在（Ignition ≤ 2.5.1 + debug 模式）
```

**版本指纹**（debug 模式下错误页 JSON 的 `env` 字段泄露，无需额外请求）：
- `laravel_version`、`laravel_locale`、`laravel_config_cached`、`php_version`
- `application_path` 泄露服务器绝对路径（宝塔面板常见 `/www/wwwroot/xxx`）
- 例：独角数卡 dujiaoka 发卡系统 = Laravel 6.20.42 + PHP 7.4.33

### 1.2 利用链

`Facade\Ignition\Solutions\MakeViewVariableOptionalSolution`（`RunnableSolution`）的 `viewFile` 参数直通 `file_get_contents` + `file_put_contents`，无 `@` 抑制、无路径校验：

1. **日志污染**：向 `storage/logs/laravel.log` 写入 base64 编码的 phar
2. **物化 phar**：用 `php://filter/write=convert.base64-decode` 等多级过滤器链还原 phar 二进制
3. **触发反序列化**：`phar://<log>/test.txt` 使任意文件操作触发 phar 元数据反序列化 → PHPGGC gadget 链 RCE

```bash
# 生成 phar（fast-destruct -f 更稳定）
php -d'phar.readonly=0' phpggc -p phar -f Monolog/RCE1 system "id" -o exploit.phar
# Laravel 6 用 Laravel/RCE2；Laravel 8 用 Laravel/RCE9 / RCE11；Monolog 2.x 用 Monolog/RCE1
```

### 1.3 关键坑（实测，省数小时）

| # | 现象 | 结论 |
|---|---|---|
| 1 | `file_get_contents(不存在文件)` 返回 **200 空**（非 500 错误页） | 目标 `error_reporting` 排除了 `E_WARNING` → warning 不写 laravel.log → 官方 ambionics PoC 的日志污染失效。症状：convert 成功但 `phar://` 读返回 200 空 |
| 2 | 无效 `solution` 触发 `abort(404)` | payload 落在 `request_data.body.solution`（Ignition 错误页 JSON），Laravel 日志只记异常对象，不写 request_data → solution 参数污染无效 |
| 3 | `php://filter` read/write 共用一个 `resource` | 无法单次调用读 `.env` 写 `public/`；需两步或放弃 |
| 4 | `RunMigrationsSolution` / `GenerateAppKeySolution` | 只跑固定 `Artisan::call('migrate')` / `key:generate`，无命令注入 |

**决策规则**：若命中坑 #1（warning 静默），立即放弃日志污染 RCE 路径，转向 SSH/FTP 弱口令、订单/业务逻辑、其他 CVE —— 不要像本类案例那样在日志污染上耗数小时。

完整命令、过滤器链、全部已试死路与源码核对：见 [references/cve-2021-3129-laravel-ignition-rce.md](./references/cve-2021-3129-laravel-ignition-rce.md)

---

## 2. 其他 PHP RCE 向量（扩展点）

- **LFI → 日志污染 → RCE**：向 Apache/Nginx 访问日志、PHP session 文件写入 `<?php ... ?>`，再 LFI 包含
- **phar 反序列化**：任意 `phar://` 文件操作触发（详见 deserialization-insecure / deserialization-testing）
- **SSTI / 反序列化 / 文件上传**：见对应专项技能（ssti-server-side-template-injection、deserialization-*、file-upload-testing）
