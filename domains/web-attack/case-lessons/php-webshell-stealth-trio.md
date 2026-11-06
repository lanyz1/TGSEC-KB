# 案例课：PHP 大马隐身三件套（内存盘落点 / Cookie 盐认证 / 关缓冲）

> 来源：同行样本拆解（2026-10）· 域：web-attack / webshell
> 原文与凭据不入库；本文只留可复用手法。

## 一句话

PHP 大马被抓的三大原因是「落在 web 根」「有登录页」「回显慢」，对应三处改动即可同时消掉：**落 `/dev/shm`、用 `Cookie: postpass=md5(pw+salt)` 认证、回显前发 `X-Accel-Buffering: no`**。

## 前提 / 指纹

- 已拿到 PHP 执行权限（上传/包含/RCE 任一），且 `disable_functions` 未禁 `file_put_contents`
- 指纹：样本内出现 `postpass` cookie 名、`/dev/shm/.` 路径、`X-Accel-Buffering`
- 无 cookie 时响应为空白或 `exit`，**不返回登录表单**

## 链

```text
写马到 /dev/shm/.<rand>  →  Cookie: postpass=<md5(pw+salt)>  →  带 cookie 才执行
→ header('X-Accel-Buffering: no') 保证命令回显即时输出
→ error_reporting(E_ALL & ~E_NOTICE & ~E_WARNING & ~8192) 压掉路径泄露
```

- **落点优先级**：`/dev/shm/.`（tmpfs，不落盘、重启即消）→ `sys_get_temp_dir()/.` → web 根下的静态目录（最差）
- 文件名：点开头 + 8 位随机串，避免目录列表和常规扫马字典命中
- 认证：不存明文口令，`md5(password + 硬编码 salt)` 与 cookie 比对；salt 写在马内
- 错误 cookie 的响应要与「文件不存在」**逐字节一致**（同状态码 + 同长度空体），否则就是存在性预言机
- 假点：`/dev/shm` 挂 `noexec` 只影响执行二进制，PHP 仍由 FPM 解释执行，不影响马

## 判据与边界

- 命中判据：带正确 cookie 的 `?c=id` 回 `uid=...`；去掉 cookie 立刻空响应
- 失败边界：
  - Apache + mod_php 不认 `X-Accel-Buffering`（那是 nginx 的），仍会等整页；换 `ob_end_flush()` + `flush()`
  - `open_basedir` 限制时 `/dev/shm` 不可写 → 退到 `sys_get_temp_dir()`
  - PHP-FPM 池 `clear_env` 会让马拿不到环境变量；命令里显式给 PATH
  - 容器内 `/dev/shm` 常只有 64MB，别往那写大文件
- 同族变体：JSP 马用「错 key 回单字符 `n`」做反扫马；ASPX 马用 `Request.Headers` 取密钥；都遵循「错凭证响应 == 不存在响应」

## 检查清单

- [ ] 先确认目标 web server 是 nginx 还是 Apache，决定缓冲头
- [ ] 写马前确认落点可写、可被 FPM 读到（同 open_basedir 内）
- [ ] 用错误 cookie 与不存在路径各测一次，确认响应一致
- [ ] 上线后立刻按 `webshell-stealth-persistence` 补自愈层（cron + timer + rc.local + profile.d）
- [ ] 收尾时同清四层，否则 5 分钟内复活
