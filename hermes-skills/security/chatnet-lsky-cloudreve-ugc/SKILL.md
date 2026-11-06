---
name: chatnet-lsky-cloudreve-ugc
description: "Use when ChatNet/LskyPro/Cloudreve UGC cluster."
version: 1.0.0
---

# ChatNet + LskyPro + Cloudreve UGC 集群

圆子/Yztic 类：同开发者挂聊天(ChatNet) + 图床(LskyPro) + 网盘(Cloudreve) + 图片 API SSRF；OSS AK 常是**主账号根钥**。

## When to Use

- OnCodes ChatNet / `chat*.*/ajax/` / `add-profile`
- LskyPro 图床注册页；Cloudreve 网盘
- 同段还有 ThinkAdmin/ThinkPHP 商城、短链、Flarum
- 不要用：纯 CF 溯源（走 cf-hidden-origin-tracing）；纯 OSS 面板（走 self-hosted-panel）

## 高 ROI 链

```text
LskyPro 注册 mass assignment is_admin=1 → 超管
→ 后台读 OSS/COS AK
→ ListBucket / 下 chatnet 源码包
→ ChatNet POST /ajax/add-profile user_type=1（无鉴权建管）
→ 拖用户/私聊；同一 AK 读写网盘 uploads/
→ GetCallerIdentity = root → Cloud Assistant RunCommand → ECS root
```

## ChatNet（主入口）

- `app/ajaxController.php::add_profile()`：**无身份校验**，`user_type` 直接入库
- CSRF `verifyToken` 常整段注释
- `POST /ajax/add-profile` 空会话即可建 `user_type=1`
- `POST /ajax/save-profile` 带 `user_id` 进「改他人」分支（可达性用畸形字段证明鉴权已越过；**纪律上勿改真号**）
- `POST /ajax/get-message` 无归属 → 未登录拖私聊
- 后台写簇：`delete_users` / `update-settings` / … 无 admin 校验（探路用空参数，别破坏）

## LskyPro

- 注册字段可写 `is_admin=1`（mass assignment）→ 系统页明文云密钥
- 版本常见 1.6.x；打完删测试超管

## Cloudreve / OSS

- AK 签名：canonical 子资源空串，否则 SignatureDoesNotMatch
- 验证：List / GET / PUT marker / DELETE marker
- **根 AK 判定**：`GetCallerIdentity` 是否 `acs:ram::...:root`
- 根钥 → `RunCommand` Username=root（云助手）= 主机沦陷

## 旁路

- `api.*/ico/?url=` 类盲 SSRF（先问是否打 IMDS）
- ThinkAdmin 验证码回显 + SEM 口令碰撞
- WP 会员站开放注册 + 订单 BOLA（旁站）

## 坑

- pages.dev Functions 下线后只剩公开 R2，别死磕 API
- OSS 子资源签名细节错会误判「密钥废了」
- ChatNet 多库副本（chat / chat3）清测试号要三库查
- 未授权写簇探路用空值 return，禁止删生产

## 检查清单

- [ ] Lsky 注册能否写 is_admin？
- [ ] ChatNet add-profile 无 Cookie 能否 user_type=1？
- [ ] get-message 未登录是否 20/20？
- [ ] OSS AK 是根还是子？RunCommand 是否允许？

## 相关

- case: `domains/api-security/case-lessons/chatnet-lsky-cloudreve-ugc.md`

## Cloudreve 存储策略任意路径写 → root
- 管理员 `PUT /api/v4/admin/policy/{id}` 改本地策略：
  `{"dir_name_rule":"/root/.ssh","file_name_rule":"{originname}"}`
- 上传 `authorized_keys` 即写目标绝对路径；Cloudreve 以 root 运行则文件属主 root
- 同法可写 `/etc/cron.d/`、web 根 webshell；打前记录原策略，打完 PUT 回去
- 前置：管理员会话（弱口令 / `/api/v4/user/search` 枚举邮箱）+ 本地存储策略
- 完整链见 `subconverter-pentest` 的 V3
