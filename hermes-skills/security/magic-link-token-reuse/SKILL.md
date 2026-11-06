---
name: magic-link-token-reuse
description: >-
  Use when 平台有「免密登录链接 / tokenlogin」接口：token 经接口批量返回、可重复兑换、长期有效，拿到
  任一条即等于该账号会话。含枚举接口定位、兑换时序、单点冲突探测与影响面口径。
---

# 免密登录 URL / token 可重复兑换

## 指纹
- 前端出现 `autoLoginToken`、`mianmi`、`magic`、`tokenlogin`、`/login?token=`、`免密登录` 字样
- 后台/运营接口有 `getusermianmiloginurls`、`getuserloginurl`、`loginUrlList`、`freeLoginUrl`

## 挖掘顺序
1. **接口枚举**：从 bundle 抽 `*mianmi*`、`*freeLogin*`、`*tokenLogin*`、`*autoLogin*` 路径
2. **批量返回**：`GET /api/xxx/getusermianmiloginurls?userId=...` 常一次回多条长期有效 URL（一条=一个会话）
3. **兑换**：`GET <url>` 或 `POST /api/login/tokenlogin {token}` → Set-Cookie / 返回 sid
4. **可重复性**：同 token 连兑 3 次，三次都发新 sid 且旧 sid 不失效 = 无一次性约束
5. **长期有效**：隔 24h 再兑；token 里常无 exp 或 exp 极长

## 放大点
- token 出现在：客服工单、短信、日志、Referer、前端 localStorage、分享链接、邮件归档
- 与「登录 IP 历史」「设备列表」接口组合 → 定位 + 绕 IP 风控
- 会话单点冲突：新登录挤掉旧会话 → 可用于定向踢人（DoS）或判断账号是否在线

## 判据
- 同 token 二次兑换返回 200 且 sid 不同 → 可重放
- 兑换出的 sid 调 `/api/user/info` 返回目标账号资料 → 会话有效
- 若服务端仅校验「会话有效」不校验角色 → 叠加 `api-authorization-and-bola` 的越权面

## 交付口径
- 只统计「可兑换成功」的条数，不导出无关账号 PII
- 记录：接口路径、token 长度/前缀 4 位、有效期实测、可重放次数
