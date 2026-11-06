---
name: client-runtime-config-mining
description: "Use when a client bundle carries runtime config."
version: 1.0.0
tags: [recon, bundle, h5, spa, apk, dnsswitch, antiblock, whitelist, config]
related_skills: [anti-block-fleet-mapping, spa-js-api-mapping, cloud-storage-bucket-recon, apk-recon]
---

# 客户端运行时配置侦察

前端 bundle 里的**运行时配置**往往比扫目录值钱：换线开关、备用域名、后端覆盖地址、上传白名单、
第三方 key、客服/社群入口都写死在里面。运营方为了“防封 + 多线容灾”必须把这些下发到客户端，
于是它们的**总开关**也一起下发到了我们手里。

## 何时用

- 目标是 CN App / H5 / uni-app / Expo，前端 bundle 可下载
- 主域被 CF/EdgeOne 封、找不到源站或“下一套后台”
- 要判定上传/导出接口的白名单边界（能不能托管 HTML、能不能穿越目录）
- 已拿到一堆资产但不知道为什么有多个 API 域名

## Procedure

### 1. 拿全量 bundle（entry 只是目录）

抄 `index.html` 的 asset 清单，再把 entry 里引用的 chunk 全下下来。Vite 命名规律好抓：

```
[\w-]+-[A-Za-z0-9_-]{8}\.js
```

一次会话实测 117 个 chunk / 4 MB；配置常量在 entry，**业务端点/白名单在 chunk**，只读 entry 会漏。

### 2. 按关键字表 grep（先 grep，再逆混淆，别反过来）

| 关键字 | 意义 |
|---|---|
| `DNS_TARGET_DOMAIN` / `DNS_BACKUP_DOMAINS` | 换线开关（见 §3） |
| `dns.alidns.com` / `dns.google` / `resolve?name=` / `type=TXT` | DoH 解析器 |
| `overrideBaseUrl` / `hostHeader` | 多后端 + 自定义 Host 直连 |
| `API_BASE_URL` / `baseURL` / `VITE_` | 后端地址与构建期变量 |
| `appKey` / `publicKey` / `tenant` | 租户标识（多为设计上公开） |
| `folder` / `whitelist` / `仅允许` | 上传/导出白名单 |
| `cms/contact` / `客服` / `t.me` | 官方客服与社群入口（社工投递面） |

### 3. DNS TXT 换线开关（最强一手）

App/H5 启动时去 DoH 查一条 TXT 拿当前线路——**运营方换域名前必须先改这条 TXT**。

```
curl -s "https://dns.alidns.com/resolve?name=<target>&type=TXT"
# Answer[type==16].data → 去首尾引号 → base64 -d → "https://a,https://b"
```

- 解出来是逗号分隔 url 列表 = **当前全部可用线路**（客户端按序探活）。
- 换线域通常**只有 TXT、无 A 记录**：它不是站点，是开关。
- 线路表里的域名才是真攻击面；同 apex 下其它 label、CT 历史名都值得顺手看一眼。
- 轮询 + diff（`scripts/dns_switch_probe.py`）能**在新域名上线时先手**，常比子域爆破更早拿到下一套后台。

### 4. 线路覆盖 = 可能直连源站

`overrideBaseUrl` + `hostHeader` 说明客户端能切到**另一套后端并自带 Host 头**。浏览器带不了 Host，
但说明服务端按 Host 分虚拟主机 —— 拿这些 Host 去打已知 IP，常能命中源站/备用后台。

### 5. 白名单错误文案 = 配置导出器

上传/导出接口用三发把边界问出来：

1. 传一个不在白名单的 `folder` → 错误文案**列出全部允许值**（业务 PII 面直接暴露）
2. 改后缀传 `x.html` → 后缀白名单
3. 传 1x1 假图 → 是否真解析内容（假图被拒 = 有内容校验，别想伪魔数）

### 6. 无鉴权配置端点优先拉

`module-config` / `client-config` / `config/events` / `agreements` / `public-key` / `cms/contact`
这类接口常年免鉴权，里面常有：开关列表、第三方 key、客服/社群链接、支付与提现配置。
即使返回值“看着没数据”，也要用真实 Origin 再试一次（CORS 白名单常按 Origin 放行）。

### 7. 对账

把 bundle 里出现的**所有 host** 与已知资产表 diff，新 host = 新面（本次靠这招拿到第二个 Web 实例与存储桶）。

## Pitfalls

- **base64 ≠ 加密**：TXT/配置里那串 `aHR0cHM6...` 就是明文域名的编码，`base64 -d` 即得；不要绕去猜密钥。
- **TXT 是当前值不是历史**：要历史只能靠你自己轮询落盘；一旦运营方换线，旧值就没了。
- **只看 entry 会漏**：配置在入口、业务端点在 chunk，117 个 chunk 里才有上传/导出/团队接口。
- **`appKey`/`publicKey` 多是设计上公开的**：能证明租户归属，不能直接当越权/漏洞报。
- **`overrideBaseUrl`/`hostHeader` 只在原生容器生效**：浏览器没法带 Host，别在网页端白试。
- **“管理端 SPA 200” ≠ 后台可打**：SPA 对任意路径回 200，必须打 `/admin/auth/login` 看 JSON 错误码才能确认后端在。
- 配置里的硬编码 AK/SK 要先验形态（`AKID`/`LTAI`/`secret[:=]`），管理端 chunk 里多数是空的；
  别把一段看着像密钥的常量直接写进报告。

## Support files

- `scripts/dns_switch_probe.py` — 解析 TXT 换线开关，打印线路表并 diff 出新增域名（可 cron 轮询）。
- `references/zglw-ofssi-case-20261027.md` — 完整实测：ofssi.com 换线域、TXT 解码、上传三探原文、117 chunk 结果。
