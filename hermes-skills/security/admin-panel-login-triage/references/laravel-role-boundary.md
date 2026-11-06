# Laravel 角色边界与批量赋值判据

## 批量赋值字段

注册/改资料常见可注入字段:

`is_admin` / `isAdmin` / `role` / `role_id` / `user_type` / `type` / `level` / `group_id`

- 全部被 `$fillable` 过滤 = 批量赋值死,停手;不要换大小写/下划线变体反复打。
- 字段被过滤时,转 IDOR/业务逻辑/其他子域。

## 403 vs 302

- `GET /admin` → **403**:已登录但角色不足(角色中间件拦)。账号有效,差的是角色;别再试路径绕过。
- `GET /admin` → **302 → /login**:未登录。先补登录态,再谈角色。
- 把两者混淆会把「角色不足」误判成「未登录」,反复做无效登录。

## 登录 POST

- 带 `laravel_session` + `XSRF-TOKEN` cookie 和 `_token`。
- 失败响应看文案/重定向,不要只看状态码。
