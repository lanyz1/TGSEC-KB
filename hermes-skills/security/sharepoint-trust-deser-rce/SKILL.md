---
name: sharepoint-trust-deser-rce
description: "Use when 打 SharePoint `/_trust`：WS-Fed 反序列化。"
---

# SharePoint `/_trust` WS-Federation 反序列化（CVE-2026-45659 簇）

CVSS 9.8，**CISA KEV 收录**。修复：2026-07 更新 **KB5002882**。

CVE 簇（同一原语，四个编号）：**CVE-2026-50522 / 45659 / 56164 / 58644**

影响：SharePoint Server **2016 / 2019 / Subscription Edition**

## 一发请求

```
POST /_trust/default.aspx HTTP/1.1
Content-Type: application/x-www-form-urlencoded

wa=wsignin1.0&wresult=<URL-encoded WS-Fed sign-in response>
```

`wresult` 里的 `SecurityContextToken` 带一个 `<Cookie>` 元素：**base64 → DEFLATE 解压 → BinaryFormatter 流**。
服务端解压后**无限类型反序列化**，在 `w3wp.exe` 里跑，身份是 **web 应用池账号**。

## 一石二鸟：RCE + 机器密钥

同一个原语可以**在进程内直接 dump 整个 farm 的 machine keys**（`ValidationKey` / `DecryptionKey`）。
默认配置的 farm 上：**无子进程、无 AV 告警、无外连 beacon**——因为它压根不需要落盘或连外。

拿到 keys 之后：

```
伪造 __VIEWSTATE  → 不用再打一次反序列化洞
伪造 auth token   → 直接冒充任意用户（含 farm admin）
```

**这就是为什么只打补丁不够。** 已经被打过的 farm，补丁装上了，攻击者手里的 keys 照样能伪造 ViewState 一直到你轮换它们。

## 处置优先级

1. 打 KB5002882
2. **轮换 machine keys**（所有场）
3. 猎 `/_trust` 请求签名——四个变体里**唯一都存在的痕迹**
4. 查 4624/4648 里 `w3wp.exe` 起的异常登录

## 检测视角（对蓝队报价用）

- **AMSI 对 `/_trust` 请求体做扫描**能直接拦住（最有效的一层）
- 正常业务**不应**有外部直接 POST `/_trust/default.aspx` 的流量——这条规则零误报

## 坑

- `wa=wsignin1.0` 和 `wresult=` 两个参数缺一不可，缺了服务端直接 302 回登录
- 反序列化 gadget 依赖 .NET 版本与已装组件；SE 和 2016 的可用 gadget 集不一样，PoC 要按版本换
- 回显不在 HTTP 响应里（异步 worker），必须带外或靠后续 keys 伪造来验证
