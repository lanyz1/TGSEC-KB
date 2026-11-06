---
name: asset-discovery-osint
description: 资产测绘与目标发现。Use when finding new targets via FOFA asset-search, or when the user asks to "找目标/找XX类型的站/自己找打"…
---

## GVA 魔改直播 SaaS h5 免登链打法（2026-10 实战）

目标特征：GVA/gin-vue-admin 魔改直播电商 SaaS，存在无鉴权 `POST /api/h5/debug/loginLink`。

1. **别信前人的 roomId 扫描范围**：实战中前人只扫 1-20/100 即下「直播间不存在」结论，真实房间在 212-222。GVA 自增 ID 至少扫满 1-2000（并发 GET oracle）再下结论。
2. loginLink 必常参数 `{"roomId":N,"h5BaseUrl":"https://任意域"}`——缺 h5BaseUrl 报「缺少H5根地址」，任意串即过。
3. 返回即**完整 viewer JWT**（HS256/iss qmPlus/aud=["H5"]，含真实 customerId/tenantId/unionId）。终端只显示 `eyJhbG...fR7s` 时先怀疑**显示层截断**——写文件读字节数验证，勿急判服务端脱敏。
4. viewer token（x-token 头）打通 `/api/h5/order/create|list|detail|cancel`、`/api/h5/address/*`。下单 PoC 用后即取消，保留现场。
5. 配套无鉴权读面：`/api/h5/live/products?roomId=`、`/api/h5/live/productDetail?roomId=&productId=`、`/api/h5/live/status?roomId=`。
6. IDOR 检验：他人 orderId 若返「订单不存在」= customerId 过滤到位；viewer token 打管理端 /api/user/* 报「无效的系统用户凭证」= aud 校验到位，跨面提权死。
7. JWT 伪造判据：qmPlus/qmPlus!@#/qm_plus 出厂密钥单发验证 + rockyou hashcat -m 16500 全 miss → 随机密钥，线死。

# Asset Discovery OSINT — 资产搜索与自动找目标

## 工具

`asset_search.sh` (即 asset_search.py):
- 用法: `asset_search.sh fofa "<查询语句>" [数量]`
- 带存活检测: `asset_search.sh fofa --check "<查询语句>" [数量]`
- 凭证: config.yaml `asset_search` 段 (fofa_email/fofa_key)

## FOFA 搜索语法速查

- 关键词: `title="xx"` `body="xx"` `header="xx"` `server="xx"` `app="xx"`
- 逻辑: `&&`(与) `||`(或) `!=`(非) `()`
- 字段: `ip` `port` `protocol` `country` `domain` `host` `title`

## 目标选择原则 (IMPORTANT)

**优先打容易出资产的类型, 跳过难打类型:**
- ✅ 好打: TG集成站(认证逻辑薄弱) / 未授权服务 / 弱口令面板 / 老框架RCE / 群控CRM(默认口令常见)
- ❌ 难打: 发卡SaaS(独角数卡/彩虹发卡等, 防护强) — 不要选这类目标

## 高价值指纹词库 (按可打性排序)

### 1. TG 相关 (telegram 集成站) — 最容易打, 优先
- `body="telegram-web-app.js"` — 内嵌 TG WebApp 的站点
- `body="initData" && body="tg"` — initData 可伪造的站点
- `body="t.me/" && body="login"` / `app="telegram"`
- 打法: TG auth 校验常可绕过, 类似 cats-fortune/joefortune

### 2. 通用未授权/高危服务 — 有现成利用, 好打
- `app="nacos"` / `app="druid"` / `app="swagger"` / `app="grafana"`
- `app="jenkins"` / `app="activemq"` / `app="solr"` / `app="elasticsearch" && port="9200"`
- `app="phpMyAdmin"` / `app="tomcat" && title="manager"`

### 3. 老框架 RCE
- `app="thinkphp"` / `app="shiro"` / `app="weblogic"` / `app="fastjson"` / `app="struts2"`

### 4. 群控/营销 CRM (弱口令常见, 类似 Whatcrm)
- `app="whatsapp" && title="crm"` / `app="群控"` / `title="群发"`
- `body="telegram-web-app.js" && title="crm"`
- 打法: admin/admin123 等弱口令登录 -> 后台 dump

### 5. 博彩/棋牌 (可选)
- `app="赌博"` / `title="BET"` / `body="棋牌"` / `title="casino"`
- 优先有支付回调/用户系统的

## 自动找目标流程 (自动找+自动打)

1. 收到指令"找 XX 类型目标" → 先加载本技能
2. `asset_search.sh fofa "<对应词库查询>" 50` 搜索
3. 加 `--check` 做存活过滤
4. 筛选: 存活 + 业务匹配 + 排除内网/CDN 纯静态页 + 按可打性排序
5. 汇报候选列表 → 按价值排序后在单兵会话内逐个推进（团队派单已废除）
6. 每个目标按 FINAL ASSET TARGETS 深挖, 拿不到资产不放弃

## 注意
- 搜索凭证走 config.yaml, 不硬编码
- FOFA F 点余额不足时(errmsg 含 820031): 告知用户充值或等额度, 不要反复空搜
- FOFA 高级语法(title=)和 ip="x.x.x.x" 可用, 但 header="具体版本串" 会报 [-403] 访问权限不足 → 改用 header="Werkzeug" 粗匹配再本地过滤版本
- 对找到的目标做存活探测必须走代理 (rotate_proxy.sh)
- 遇到发卡SaaS(独角数卡/彩虹发卡)等难打类型: 跳过换下一个, 不要浪费时间
- 同指纹集群发现法: 目标横幅(Werkzeug 版本+Python 版本+标题)精确组合查询 + 同 IP 多端口(如 5000/5010 双实例)是识别「同款 fork 部署群」的最强信号, 优先枚举同横幅资产再逐个比对登录页特征