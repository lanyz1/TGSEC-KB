# 案例课：PlayTube `social_login` 伪造 access_token 直接成管理员

> 来源：报告包 69pedia（2026-10）· 域：web-attack / PHP 视频 CMS

## 一句话

`ajax.php?f=social_login` 信任客户端提交的 `access_token`，而 token 只是 base64 JSON；把 `user_id` 改成 1，服务端不回源校验 provider，直接下发管理员会话。

## 指纹

- `pt_` 前缀表（`pt_users`/`pt_config`/`pt_custom_design`）
- `/admincp`、`/ajax.php`、`social_login`、`ffmpeg_binary_file`

## 链

```text
POST /ajax.php?f=social_login
server_key=<前端硬编码>&access_token=<base64({"user_id":1,...})>&provider=facebook
```

- `server_key` 常硬编码在 `themes/*/js` 或 `ajax.php` 附近
- 先抓一次真实第三方登录，记录字段名与编码；再改 `user_id`
- 响应直接 `Set-Cookie` 或返回 token = 命中

## 同 CMS 其他面

- `pt_config.ffmpeg_binary_file` 可写 → 转码时拼进 `shell_exec` → RCE（改后要触发转码队列）
- `pt_custom_design` 的 `$theme` 拼模板路径 → `../../` 写 PHP
- `cleanup.sh` 777 + root cron → 追加 setuid/反弹
- aaPanel 秘密入口 `/benderx`、`panel_default.db` 读入口与口令哈希

## 边界

- `server_key` 可能只用于服务端校验；伪造前先看真实回调字段
- 纯静态站任意写只能落 HTML/JS
- 写文件需确认 web 根可解析 PHP

## 检查清单

- [ ] `pt_` 表/`/admincp` 指纹
- [ ] `social_login` 真实回调抓包
- [ ] `user_id` 越权
- [ ] ffmpeg 配置写入 + 触发
- [ ] cleanup.sh 权限

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
