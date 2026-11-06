# 可信代理头 → 限流绕过 + 临时身份 TTL

黑盒 API 探测时,“接口通但被限”与“账号活不久”是两回事,分开处理。实测 topuplive 2026-10(Laravel + APISIX + 阿里云 ALB)。

## 1. 原理:限流键可能是客户端给的

Laravel `throttle` 取 `$request->ip()`。在 APISIX / ALB / Nginx 之后,框架默认信任 `X-Forwarded-For` / `X-Real-IP`,于是

```
-H "X-Forwarded-For: 8.8.8.8" -H "X-Real-IP: 8.8.8.8"
```

**验证方法**:拿一个已被限的端点(`Frequent sending, please try again later!`)换 5 个不同假 IP 重试。本例 5/5 全部 `success` ⇒ 限流键就是 XFF。

适用面:发码、登录、注册、全局 IP 配额、防爆破计数器。

## 2. 反面:漂移 = 自杀

同一站还有**风控层**(不是限流层),按登录地异常判分。XFF 每次乱跳时:

- 账号几分钟内被**静默删除**,不报错、不发通知
- 带 token 请求返回 `登录失效`;再登录返回 `Account does not exist`
- 本例前两个号就是这么没的

**纪律**:选定一个假 IP 后**全程钉死**(本例 `11.22.33.44`),注册/登录/下单/上传全用同一个。要换 IP 就换账号,别在同一账号上漂。

## 3. 临时身份 TTL(比限流更硬的墙)

公共临时邮箱注册的账号存活期以**分钟**计:注册 `status:1` → 下一轮调用 `登录失效` → `Account does not exist`。本例三个号全灭。

⇒ **窗口模型**:注册成功即开启一个短 TTL 窗口,窗口内必须把关键动作全部做完(领券 → pre-pay → 下单 → 上传 → 读数据)。
⇒ **禁止“先批量注册,回头再打”**,那等于批量阵亡。
⇒ 脚本结构:一个进程里跑完 register → login → 业务动作 → 落盘,不要跨调用分步。

## 4. 旁路:不受限流的同类端点

同一发码函数常按 `type`/`purpose` 分叉,风控只挂在注册那支:

- `type=register` → `Frequent sending`
- `type=resetPassword` → **不限流,且仍返回用户存在性 oracle**
- `type=bind` / `login` → 各自独立计数

注册支被限先枚举 `type` 取值,别直接放弃。

## 5. 自检清单

- [ ] 端点按 IP 限流?→ 换 XFF 试一次,别先换代理池
- [ ] XFF 绕过后账号被删?→ 钉死单值
- [ ] 账号 TTL 多长?→ 注册后立刻测 profile,隔 5 分钟再测
- [ ] 有同功能的非注册 `type` 分支吗?
