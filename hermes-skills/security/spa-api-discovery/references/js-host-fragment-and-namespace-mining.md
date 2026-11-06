---
name: js-host-fragment-and-namespace-mining
description: 从前端 JS 片段挖「活宿主」与「第二套命名空间」(CDN 死路绕行 + 多前缀契约抽取 + POST {} 零成本探未鉴权面)
---

# JS 片段挖活宿主 + 多命名空间抽契约

适用:已知的 API 域名/CDN 主机全 405/404(CDN 无源站或已下线),或某套前端的登录链在手上主机上**全 404**。

## 1. 活宿主常以「字符串片段」出现,不是完整 URL
真身后端往往只在前端 bundle 里以**比较片段**形式被引用,不在 HTML/CSS/接口清单里:

```bash
grep -ohE '.{0,80}indexOf\("https?://[a-z0-9.-]+".{0,120}' *.js      # 前缀比较式引用(最常命中)
grep -ohE '"[a-z0-9-]+\.(cftcredit|example)\.com"' *.js | sort -u   # 片段域名
grep -ohE '(al-|api-|mobile-|mobile-loans-|h5-|wap-|applet-|static-)[a-z0-9-]*\.[a-z0-9.-]+' *.js | sort -u  # 域名前缀族
```

判据与用法:
- 命中的片段**补全成 FQDN 再解析**;解析到的 IP 用直连 + `Host: <fqdn>` 请求,可越过 CDN 层(CDN 只认自己的 Host)。
- `location.origin` / `location.href` 的**端口分支**会整片泄漏环境映射(如 `port==13443→loans-test1` / `11443→loans-test2` / else prod):每个分支对应一台真后端,逐个按 IP+Host 实测;被 CDN 挡死的 prod 分支不必死磕,test 分支往往直连活着。
- 同一域名族里**只有一个**变体是直连活源(实测:`al-h5.<母域>` 直连活,`al-h5.<厂商域>` 走 CDN 全 405)⇒ 域名族要**逐个实测**,不能挑一个下手就下结论。

## 2. 抽契约要按「多前缀」,别只抽 `^/api/`
同一站点常有**多个顶级前缀 = 多个上游应用**:

```bash
cd <spa_dir> && grep -rhoE '"/(api|uranus-api|h5-v2|v1|v2)[A-Za-z0-9_/{}\.:-]*"' . \
  | tr -d '"' | sort -u > paths.txt; wc -l < paths.txt   # 打印候选数,与后续扫描数对照
```

- 出现没见过的前缀 = **另一套上游**:错误信封通常都不同(英文 `Method [GET] not allowed, allowed methods [POST]` / `Missing parameter, name: x, type: Long` vs 中文 `缺少参数，名称：x，类型：String`)⇒ **按信封分族,各自建表、各自扫**,不要混在一张命中表里判读。
- **第二套 SPA 是权威契约源**:`/h5-v2/` 与 `/h5/` 是两套应用,各有自己的 `app.js`;`grep -o '"/[a-zA-Z0-9/_{}.:-]*"' app.js` 一次出几百条路径(含 `?` 后参数名)。302 的 `Location` 把你甩到新 base ⇒ 立刻拉那个 base 的 `index.html` → `app.js` → 重抽。
- 主 JS 常是加载器,业务路径在 chunks:两个都抽,并 `sort -u` 合并。

## 3. 新命名空间的零成本探法:POST 空 JSON `{}`
新前缀多半 POST-only。`POST {}`(JSON,空体) 一发:
- `400 Missing parameter, name: x, type: Long` = 路由存在且**已穿过鉴权中间件** ⇒ 计为免鉴权面;
- 顺势一次拿到**逐字段参数名/类型表**(省掉猜参数的一轮);
- 空 body 触发不了业务 ⇒ 零副作用;但先按路径名挑出**发短信/提交/保存/回调**类跳过(名字里含 `sms`/`SendSms`/`sendCode`/`submit`/`save`/`callback`);
- 有端点会**直接返真数据**(实测:`electronic/contract {}` 泄协议清单 + 模板 ID + 内网资产路径 `mobile-loans-h5-prod.../cz-mobile-loan-h5/agreement?templateId=...&appChannel=<渠道>`)。

固定套路:① `{}` 拿参数表 → ② query/body 双位置喂真值 → ③ 每个端点都先打一发「缺参」再打「满参」,**只有满参那发返业务数据才算命中**;把 `{}`/满参 两次响应贴进战报做对照。

## 4. 拿到新面之后
- 无鉴权按 ID 查库的端点(`?orderNo=X` / `{user-id:N}`)响应区分存在性(`进件不存在` vs 数据)= 免费存在性预言机,可当枚举探针;但**必须先证明参数绑得上**(试 body 驼峰/连字符、query、form、头四种位置,响应里不再出现 `Missing parameter`/`缺少参数` 才允许进循环),否则整轮扫描是假阴性,而且「响应不同即命中」的筛法会把缺参报错读成命中。
- 新命名空间里若有签名闸,按 `signed-api-gate-oracle-hunt` 走:先找铸造器、再做对照实验(用签名 URL 原路径验证三元组当下有效)、再收敛到实例 ID。

> 关联:`signed-api-gate-oracle-hunt`(签名预言机/实例 ID 收敛)、`api-param-name-discovery`(参数名与绑定位置)、`cdn-origin-tracing`(源站定位)。
