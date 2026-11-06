---
name: asset-takeover-feasibility
description: >-
  Use when 老板问能否劫持/接管站点。五路实测矩阵定论。
---

# 资产劫持可行性判定

触发：「我要对这个站做劫持」「能不能接管」「域名能不能抢注」「子域接管」「takeover 可不可行」「DNS 劫持」。

## 铁律：先实测，再回答

老板问「能不能」时**禁止凭印象答**。五条路每条都有**一个决定性测试**，跑完再下结论。
结论交付成**证据表**（路径 / 实测输出 / 判定），不是形容词堆。老板会拿 whois 行和 HTTP 码核对。

## 五路实测矩阵

| 路 | 决定性测试 | 死路特征 |
|---|---|---|
| 域名过期 / 抢注 | `whois` 看 `Registry Expiry Date` + `Domain Status` | 未到期 且 `clientTransferProhibited` / `clientUpdateProhibited` |
| 注册商挂起 | NS 是否变成 `EXPIRE1/2.<registrar>-DNS.COM` | NS=expire + 解析到停放页 → 已被注册商按滥用挂起，**原主已失控但第三方也拿不到**（注册期还在 + 转移锁） |
| 子域接管 | 对每个已枚举子域 `dig +short CNAME` | CNAME 目标域本身活着且在注册期内 → 无悬挂可抢 |
| 对象存储投毒 | `PUT` 随机探测文件名 + `GET /?acl` | `403 AccessDenied` / `The bucket you access does not belong to you` |
| CDN / 边缘面板 | 节点**默认证书**识别真实厂商（见下） | 命中阿里云 ESA / 网宿 / Cloudflare 等头部 → 无白牌后台可打 |

## 关键技巧：默认证书识别 CNAME 背后的真实 CDN

子域 CNAME 到 `xxx.a1.initba.com`、`xxx.gccdn.net` 这种陌生域时，**别猜「白牌高防，可能有个可打后台」**。不带 SNI 直连 IP 拿默认证书：

```bash
timeout 15 openssl s_client -connect <IP>:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -ext subjectAltName | head -8
```

判读表：

- `CN=*.certfallback-esa.com` + `O=Alibaba (China) Technology Co., Ltd.` → **阿里云 ESA**（`initba.com` / `initkk.com` 这类就是它的 CNAME 接入域）
- `CN=default.chinanetcenter.com` + `O=网宿科技股份有限公司...` + SAN 含 `*.wscdns.com` / `*.v.cdn20.com` / `*.lxdns.net` → **网宿科技 CDN**（`gccdn.net` 就是它的接入域）
- `CN=*.<目标主域>` → 客户自有泛域名证书，节点按 SNI 分发，不泄露厂商

一旦认到头部厂商，**CDN 后台这条路当场判死**，不要浪费时间爆破 apex —— 这类接入域的 apex 通常**没有 A 记录，是纯 DNS 区**，本来就没 web 服务（curl 一律 `000`，不是被封）。

## 口径纪律（重要）

- 劫持做不到就**直说做不到**，不要把「向 Apple 举报吊销证书」「向注册商投诉」「向 CDN 提滥用」包装成劫持。那是**打击面**，不是**接管**，混着说会被当吹牛。
- 反过来：实测中若发现对方**盗用第三方企业的证书/资质**，单独列成打击点 —— 价值常高于劫持，且不需要碰任何第三方系统。
- 每条结论附实测输出（whois 原文行、HTTP 状态码、证书 subject）。
- 只打目标及其真关联；注册商、签名平台这类第三方即便技术上可打，先按 `scope-discipline-gate` 判越界，不要自行扩权。

## 附带情报（跑矩阵时顺手拿）

- `whois` 的 `Registrant` / 联系人邮箱：国内 `.cn` 常直接暴露公司全名 + 手机号邮箱
- 域名注册日极新（几天~几周）= 打一枪换一个的消耗品；反过来到期日很近（<60 天）= 值得排期盯 drop
- IP 段可反推采购栈：`47.246.x` = 阿里云，`138.113.x` = 网宿
- 同一秒批量注册的多个域（如两个域均 `2024-04-02 11:40:1x`）= 同一运营方同一批采购

## 参考

- `references/navbox-hijack-assessment.md` — 完整实测案例（91tx / navbox 站群，2026-10）
- `references/ios-supersign-chain-forensics.md` — 分发链上游取证：`/clientapi/` 契约、appid 定位、mobileprovision 盗证鉴定、udidconfig 挖超级签平台

## 关联

- 追源站 / CNAME：`cdn-origin-tracing`、`origin-ip-discovery`、`cf-hidden-origin-tracing`
- 越界判读：`scope-discipline-gate`
- 关联资产扩张：`fraud-network-asset-expansion`、`operator-attribution`
