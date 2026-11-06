# 9581kk.com 子域名枚举与安全扫描 (2026-07-14)

## 发现的子域名

| # | 子域名 | IP地址 | 类型 | 备注 |
|---|--------|--------|------|------|
| 1 | 9581kk.com | 43.229.4.76 (主) | A/主站 | Cloudflare CDN |
| 2 | www.9581kk.com | 43.229.5.56/57, 43.229.4.75/76, 147.161.37.37/38 | CNAME → bbet888s.leboweb.com → 3bc4306b.qcnodecd.com | CDN节点 |
| 3 | ag.9581kk.com | 34.80.211.95, 34.96.197.130 | CNAME → ag.leboweb.com | GCP(Google Cloud) 代理后台 |

## DNS 信息

| 记录 | 值 |
|------|-----|
| NS | woz.ns.cloudflare.com, macy.ns.cloudflare.com |
| MX | 无 |
| CNAME (www) | bbet888s.leboweb.com → 3bc4306b.qcnodecd.com (QCloud CDN) |
| CNAME (ag) | ag.leboweb.com (GCP) |

## 端口扫描

### 9581kk.com (43.229.4.76) — CDN背后
所有扫描端口均 OPEN (CDN代理行为): 80, 443, 8080, 8443, 8888, 7777, 9090, 21, 22, 3306, 3389

### ag.9581kk.com (34.80.211.95 / 34.96.197.130 — GCP 真实服务器)

| 端口 | 服务 | HTTP响应 | 备注 |
|------|------|----------|------|
| 80 | HTTP | 301→443 | |
| 443 | HTTPS | 200 "welcome" | Apache, /js/artDialog/ |
| 8080 | HTTP-alt | 无响应 | |
| 8443 | HTTPS-alt | 无响应 | |
| 8888 | HTTPS | 200 "欢迎光临！！！" | biying CMS 代理面板 |
| 7777 | HTTPS | 200 "欢迎光临！！！" | Same as 8888 |
| 9090 | HTTP-alt | 无响应 | |
| 22 | SSH | — | OPEN |
| 3306 | MySQL | — | OPEN (高危) |
| 3389 | RDP | — | OPEN (高危) |

## HTTP 路径探测

### 9581kk.com (主站)
| 路径 | 状态 | 说明 |
|------|------|------|
| `/` | 200 | 首页 biying CMS |
| `/m/` | 200 | React SPA (移动端) |
| `/api/Public/main/index.php` | 200 | API端点 |
| `/cl/index.php` | 200 | biying CMS 主入口 |
| `/cl/tpl/biying/` | 403 | 禁止 (模板目录) |
| `/api/` | 403 | 禁止目录列表 |
| `/app/` | 403 | 禁止目录列表 |

### ag.9581kk.com (代理后台)
| 端口 | 路径 | 状态 | 说明 |
|------|------|------|------|
| 443 | `/` | 200 | "welcome" 入口页 |
| 443 | `/app/daili/login.php` | 200 | Diamond Bet System 管理员登录 |
| 8888 | `/` | 200 | "欢迎光临！！!" biying CMS |
| 8888 | `/cl/index.php` | 200 | biying CMS 面板 |

## 技术栈
- Web: Apache
- CMS: biying CMS (PHP + React SPA)
- CDN: Cloudflare + qcnodecd.com
- 代理后台: GCP
- Session: Example_Session cookie
- WAF: mod_security (406)

## 攻击面总结
1. ag.9581kk.com (GCP) 端口3306(MySQL) 对外暴露
2. ag.9581kk.com 端口3389(RDP) 对外暴露
3. ag.9581kk.com 端口22(SSH) 对外暴露
4. ag.9581kk.com:8888 biying CMS 面板可直接访问
5. ag.9581kk.com:443 /app/daili/login.php — Diamond Bet System 管理员登录页
6. 主站 /api/Public/main/index.php API 端点无认证暴露
7. ag.9581kk.com 位于 GCP (非Cloudflare保护)，拥有真实公网IP可直接访问
