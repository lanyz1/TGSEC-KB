---
name: tg-bot-admin-panel
description: TG bot 管理后台渗透与运营验证：broadcast/群发、Playwright SPA 后台驱动、服务端故障判定。
---

# tg-bot-admin-panel — TG Bot 管理后台 / 群发广播渗透与运营验证

## When to Use

目标是 Telegram Bot 管理后台（web-admin / 控制面板），尤其是：
- 需要执行 **broadcast / 群发 / Push-рассылка / 发送给所有用户** 类操作
- 已接管管理 token，要通过 UI 或 API 触发群发、验证群发功能
- 管理后台是 React/Vue SPA，token 存 localStorage，需要 Playwright 驱动
- 群发端点报 500，需判定是「我请求的问题」还是「服务端故障」

## 核心工作流

1. **反向确认端点**：`/openapi.json` 公开时直接抄 path + schema（BroadcastBody 常只有 `text` 字段、无 target/user_id = 只能全量群发）。再看 admin JS（`api("/api/web-admin/broadcast")` 调用方式、期望响应 `{sent,total}`）。比 ffuf 猜端点快。
2. **Token 认证**：TG bot 后台常见自定义头 `X-Admin-Token`（**非 Bearer**）；token 常存 localStorage `k52_admin_token` 之类键名。`stats` 端点 200 验活。
3. **先探参数校验**（区分客户端 vs 服务端故障的关键）：
   - 空 body / 空 text → **400**（参数校验正常）
   - 超长 text → **400**（「Слишком длинное сообщение」等，长度校验正常）
   - 任意非空 text（含纯 ASCII "test"）→ **500** + 响应时间稳定（~1.2s）= **服务端发送循环内部异常**，不是 payload/认证/长度问题
4. **用 UI 复核坐实**：Playwright 打开后台 → 注入 token → 走 UI 点「发送给所有人」→ UI 同样报错 + network 面板 response-body 纯 `Internal Server Error` → 排除客户端格式因素，**判定服务端故障**。

## Playwright 驱动 React SPA 管理后台（实战技巧）

- **ref= 引擎不可用**（报 `Unknown engine "ref"`）：手写 JS 定位——`page.evaluate` + `querySelectorAll` + `find(b => b.textContent.trim()==='按钮文本')` 点击。
- **React 受控 textarea 填值**：直接 `ta.value=` 不触发 React state，提交为空。必须原生 setter + input 事件：
  ```js
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
  setter.call(ta, text); ta.dispatchEvent(new Event('input', {bubbles:true}));
  ```
- **localStorage token 注入绕过登录**：`localStorage.setItem('k52_admin_token', token)` 后重新 goto，URL hash 变 `#dashboard` 即登录态生效。
- **confirm 对话框**：`browser_handle_dialog accept=true`（点发送后 SPA 常弹「确认发送」）。
- **精确看错误**：`browser_network_requests(filter='broadcast')` 拿编号 → `browser_network_request(index, part='response-body'|'request-body')` 核对实际发送体与错误原文。
- **会话丢失恢复**：gateway 重启/页面变 `about:blank` → 重新 goto 即可，localStorage 仍保留 token。

## 服务端群发 500 根因推断（按概率）

1. **bot token 失效/未配置** → 第一次调 Telegram API `sendMessage` 就抛异常 → 500
2. **guest/占位用户负 tg_id**（如线下客人占位 -2~-91）被遍历发送 → Telegram API 调用失败 → 500
3. 无法通过 API 修复：PATCH 用户字段常被白名单过滤（仅 display_name/photo_url/rp_delta），改不了 tg_id；无其他消息端点。

## 决策纪律

- 服务端功能损坏且无 API 修复路径 → **报告结论 + 证据即停**，不要反复重试/无限枚举。
- 端口扫描若**全端口 open**（tcpmux/hostname 等全假）且延迟稳定（~0.25s）= 防火墙/IPS 对每个 SYN 回 SYN-ACK，**全 open 结果不可信**，停止逐端口验证。
- 用户判定目标「没价值」叫停时立即停，不继续后台任务。

## Pitfalls

- 空文本 400 + 超长 400 都正常 ≠ 端点正常；**只有非空文本实际发送**才暴露服务端故障。
- 删除负 tg_id 测试账号后仍 500 → 证明不是唯一原因，别在删除上死磕。
- 前端 axios 带 token 只说明客户端打算带；服务端是否校验要无头 curl 复核。
