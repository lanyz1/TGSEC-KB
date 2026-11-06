# Cloudflare Flexible SSL + 源站直连 — xinbi.com 实战

> 来源：xinbi.com 20 阶段全链渗透报告 P4-01 / P8-01 / P18-01

## 典型架构

```
用户 ──HTTPS──→ Cloudflare ──HTTP(80)──→ 源站（Flexible SSL）
                                          ↑
                                   明文传输区间
                                   签名头/Cookie/请求体全裸
```

## 三种源站暴露路径

### 路径 A：子域 CNAME 泄露
```
integrate-safew.xspay.vip → 126.214.108.58（直接解析到源站 IP）
```

### 路径 B：A 记录即源站
```
xinbipay.com → 18.141.84.252 / 47.242.180.239（两台均可直连）
```

### 路径 C：独立域名
```
app.xbpay.vip → 153.43.76.31（生产 App API 源站）
```

## Host 头 vhost 枚举结果

### 源站 126.214.108.58（xspay.vip 集群）

| Host | 状态码 | 说明 |
|------|--------|------|
| api.xspay.vip | 200 | ✅ API 直连（无 WAF） |
| official-ui.xspay.vip | 200 | ✅ Nuxt 站点 |
| integrate-safew.xspay.vip | 403 | SafeLine 规则拦截 |
| 其他 22 个候选 | 404 | 未配置 |

### 源站 18.141.84.252 / 47.242.180.239（xinbipay 集群）

| Host | 状态码 | 说明 |
|------|--------|------|
| www.xinbipay.com / xinbipay.com | 200 | Nuxt3 站点（含 /api 反代） |
| app.xbpay.vip | 400 | API（需 Accept-Language 头） |
| main-agent.xbpay.vip | 467 | SafeLine 身份认证 |
| main.xbpay.vip | 403 | CDN 错误页 |
| 其他 22 个候选 | 530 | nginx 错误页 |

## 明文回源证据链

```
# 源站 443 测试
curl -skI https://126.214.108.58/ -H "Host: api.xspay.vip"
→ 404（443 上 api vhost 未配置）

curl -sI http://126.214.108.58/ -H "Host: api.xspay.vip"
→ 200（80 上正常服务）

# 结论：CF 配置 Flexible SSL，源站仅在 80 提供 api/official-ui
```

## Flexible SSL 的五种利用场景

1. **中间人截获**：CF 边缘→源站链路上可截获 API 签名头、Cookie、请求体
2. **跳过边缘防护**：直连源站 80 → 无速率限制、无 Bot 管理、无缓存规则
3. **WAF 消失**：源站上的路径（如 `/server/*.mjs`）不再被 CF WAF 拦截
4. **vhost 探测**：同一源站上可能有隐藏的管理面板/测试环境
5. **App 明文通信**：APK 内基址为 `http://app.xspay.vip`（明文 HTTP）

## 与 cloudflare-bypass Skill 五路径的映射

本案覆盖了路径 A（找源站直连）+ 路径 B（伪造 CF 头在源站上的 SafeLine 绕过）：
- A.找源站：子域 CNAME / A 记录直连 / 独立域名
- B.伪造CF头：XFF=源站自身 IP 绕过 SafeLine（仅 integrate-safew 有效）

## 邻段扫描

```
# 126.214.108.50-70 范围扫描
仅 .58 存活（其余超时/拒绝）

# 153.43.76.31 独立
非共享主机
```

## S3 桶对象公网可读

```
# dev 桶（东京）
https://xpay-dev-s3.s3.ap-northeast-1.amazonaws.com/xpay_v1.6.0_test_20260826_v1.apk → 200

# prod 桶（香港）
https://xpay-prod.s3.ap-east-1.amazonaws.com/xpay_0827_pro.apk → 200

# 两个桶均 403 ListBucket / ?acl
```

## 测绘引擎适配

1. Flexible SSL 是最常见的 CF 配置错误 — 源站 80 直接服务 = 全部边缘防护无效
2. 判定方法：源站 IP 的 443 返回 404/默认证书 + 80 返回 200 = Flexible
3. 同一运营方常有多个集群（xspay/xbpay/xinbipay）→ 全部追踪
4. S3 桶名通常是 `{品牌}-{dev|prod|upload|bucket}` → 枚举 ListBucket/对象名
