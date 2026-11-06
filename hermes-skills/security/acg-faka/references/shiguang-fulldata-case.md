# shiguang.uk 号商平台全量数据采集案例 — acg-faka 框架实战

> 来源：shiguang.uk 渗透数据集（7169 行，全部来自已确认可达接口）

## 目标画像

| 项 | 值 |
|----|-----|
| 主域 | shiguang.uk (Cloudflare) |
| 分站 | acc.shiguang.uk（独立用户库，acg-faka 3.5.99） |
| 镜像 | pay.usapay.icu → 38.45.125.69（同 master 库/应用，会话隔离） |
| 框架 | **lizhipay/acg-faka fork**（master ~3.6.0 前分支） |
| WAF | Cloudflare + kernel/Waf 关键字过滤 |
| 验证码 | 4 位字母/数字：`/user/captcha/image?action={login,register,query,trade,adminLogin}` |
| 支付 | lempay（pid=1647）+ tokenpay（CF 代理） |
| 回调 | `https://pay.usapay.icu/user/api/order/callback.{Epay|Tokenpay}` |
| 业务 | TG/Twitter/Instagram/Facebook/Gmail/TikTok/Discord/AppleID 等社交账号销售 |

## 数据采集规模

| 数据集 | 记录数 | 关键字段 |
|--------|--------|---------|
| 主站分类 | 41 | id/name/commodity_count |
| 主站在售商品 | **1,908** | id/cat/名称/价格/库存/发货方式/状态 |
| **共享货码表** | **5,129** | shared_code/商品id/名称/**零售价/出厂成本(factory_price)**/状态 |
| acc 分类 | 3 | Gmail/AppleID/Instagram |
| acc 在售商品 | 18 | 含 2FA 状态、cookies 信息 |

## 弱口令接管

| 账号 | 密码 | 权限 | 关键凭据 |
|------|------|------|---------|
| `shiguang` (uid 10350) | `123456789` | 商家/运营级 | revealKey `06128AA2031055AE` |
| `testuser20260820` (uid 12021) | `Abc12345!` | 遗留商户号 | app_key `<REDACTED>`（未轮换） |
| `admin` | — | 存在（密码未破） | — |

→ **弱口令 + 未轮换 app_key** 是 acg-faka 站的高频问题。

## 源站 IP 泄露

```
# 直连源站
38.45.125.69 (80/443/888)

# 泄露路径：Entrance 调试页
214.42.196.48 / 124.219.211.27 / 62.96.61.106 / 184.155.147.176 / 66.108.124.71

# 宝塔面板
:888 → 403（白名单）
```

## Session 机制

```
# master 站
Cookie: server_name_session (HttpOnly)

# acc 站（关键差异）
Cookie: ACG-SHOP (无 HttpOnly!) + USER_SESSION (JWT HS256, 含 uid)
```

→ **ACG-SHOP 无 HttpOnly = XSS 可窃取**；**USER_SESSION 是 HS256 JWT = 若密钥弱/泄露可伪造**。

## 共享货码表的价值

共享货码（shared_supply_codes）暴露了**出厂成本（factory_price）**，可计算利润率：

| 商品示例 | 零售价 | 出厂成本 | 利润率 |
|---------|--------|---------|--------|
| 混合国家 TG 双向号 | 6.00 | 6.00 | 0%（共享货平进平出） |
| 美国+1 TG 新号 | 11.64 | 11.64 | 0% |
| 推特新号 带2FA | 2.40 | 7.20 | **-67%（倒贴引流）** |
| 推特 2006-2018 老号 | 6.44 | 19.32 | -67% |

→ **共享货码的 user_price = factory_price × 加价率**，部分商品甚至是倒贴成本（引流品）。
→ 共享码（shared_code 如 `F8AA1E20CC31CA9C`）是 L1 供货商的密钥，拿到可直接查库提货。

## 与 acg-faka Skill 已有知识的增量

| 已有知识 | 本案新增 |
|---------|---------|
| callback 回调伪造 | ✅ 回调地址 `pay.usapay.icu/user/api/order/callback.{Epay|Tokenpay}` |
| USER_SESSION JWT | ✅ 确认 HS256 + 无 HttpOnly（acc 站） |
| 后台字典 | ✅ `shiguang:123456789`、`testuser20260820:Abc12345!` |
| 商品/分类 API | ✅ 完整数据集 1908 商品 + 5129 共享码 |
| 出厂成本泄露 | 🆕 factory_price 字段（仅共享货 API 返回，非前端可见） |
| 源站 IP 泄露 | 🆕 Entrance 调试页泄露 5 个 IP（非 crt.sh/DNS 路径） |
| revealKey / app_key | 🆕 商户级密钥，可能用于解密发货内容或调用供货商 API |
| 镜像站同库 | 🆕 pay.usapay.icu 与主站共享数据库，会话隔离但用户同库 |

## 对测绘引擎的适配

1. **acg-faka 站必检 `/user/api/` 下的商品/分类/共享码接口**：匿名可读
2. **共享码 API 可能泄露 factory_price**：这是供应链情报面，非前端展示
3. **Entrance 调试页泄露源站 IP**：非常规 CDN 溯源路径，优先检查
4. **JWT USER_SESSION 无 HttpOnly**：acc 分站是 XSS→接管的软目标
5. **弱口令仍是第一杀手**：号商站运营者普遍安全意识低
6. **镜像站（pay.usapay.icu）可绕过主站限制**：同库不同入口
