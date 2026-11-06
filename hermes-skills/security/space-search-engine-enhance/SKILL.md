---
name: space-search-engine-enhance
description: "360Quake/FOFA测绘时使用。触发: quake.360, Quake语法, FOFA批采。"
version: 1.0.0
license: MIT

---

# 360Quake / FOFA 测绘增强卡

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收。补强你现有 space-mapping-engine-recon(Shodan/Fofa/Censys)的 **Quake 语法与批采规范**。完整卡: 镜像 `.cursor\skills\quake\SKILL.md`(547行) + `fofa-search\SKILL.md`。

## Quake 精度分级(已验证,不可违背)
| 级别 | 搜索方式 | 可信度 |
|:----:|---------|:------:|
| A | `domain:"xxx.com"` | 🟢 可信 ~0% 误报 |
| B | `"精确短名"` | 🟡 部分可信 |
| C | `"精确公司全名"`(聚合) | 🟡 知有资产拿不到 IP |
| D | `body:"关键词"` / 无引号 | 🔴 70-99% 误报 |

**例外**: 中小企业/特有产品名,body 搜索反而更准。判断: 命中 IP ≤10 且标题全指向目标 → 可信;>50 且混杂 → 误报。

## Quake API 硬限制(2026-07 实测)
- 单次最大返回 **100 条**(size>100 返空);分页 `start=0/30/60` 有效,start+size>100 返空
- **total>100 只能拿前 100** → 用子域名/IP段细分查询拼凑全量
- `quake_host` 索引对中文无效;API 只返 HTTP/HTTPS(Redis/MongoDB/SSH 端口只有导航页能看到)

## Quake 操作方式
```python
# 方式 A(推荐,数据最全,含非HTTP端口): 导航搜索结果页
# URL: https://quake.360.net/quake/#/searchResult?searchVal=<URL编码>&selectIndex=quake_service&latest=true&size=30
# 解析: 头部 "共X条,含Y个独立IP" → total/uniqueIP;每条含 [hostname][IP][端口][协议][组织][标题]

# 方式 B(结构化 JSON,只含 HTTP): 页面内 JS fetch + credentials:'include'
# 铁律: 绝不用硬编码 Authorization / 绝不用 network_request / 绝不轮询分批 start
fetch('https://quake.360.net/api/search/query_string/quake_service', {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  credentials: 'include',
  body: JSON.stringify({query, latest: "true", start: 0, size: 100})
})
```
前置: Edge/Chrome 已登录 quake.360.net,CDP 驱动带登录态。

## FOFA 批采规范
- **只许**用 config 里的 Yanbai VIP key(email+32位),**禁止** fofoapi.com 免费号/历史硬编码
- 额度不足 `[820031] F点余额不足` = 用错号或额度尽 → 核对配置再减 size
```bash
# 官方 API(从配置取 key,不打 fofoapi.com)
qb=$(printf '%s' "QUERY" | base64 | tr -d '\n')
curl -sk "https://fofa.info/api/v1/search/all?email=$FOFA_EMAIL&key=$FOFA_KEY&qbase64=$qb&fields=host,title,ip,port,domain,protocol&size=100"
# 响应 {"error":false,"size":N,"results":[...]};多页加 &page=2
```
- 常用: 子域 `domain="x.com"` / IP 反查 `ip="1.2.3.4"` / 指纹 `body="..."` / `protocol="mysql"` / 组合 `domain="x.com" && port="8888"`
- **排除中国站必须 CN+HK+MO+TW 全排除**(HK 不算"非中国")

## 批采流程(用户规范)
1. 15-20 组查询 × 3-5 页,每页 100;排除 CN/HK/MO/TW
2. 筛活 → 按框架/指纹分类 → delegate_task 下发(每组 10-20 目标)
3. 每目标必测: admin/login/api/swagger/docs/install/robots.txt/.env + 框架 + 默认密码
4. 发现高管/疑似后台深度下发;用户说"太少了" = 扩量

## 完整情报
镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\quake\SKILL.md` + `fofa-search\SKILL.md`
