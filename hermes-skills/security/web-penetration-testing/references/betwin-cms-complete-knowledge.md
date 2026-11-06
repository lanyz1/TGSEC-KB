# BetWin CMS — 完整知识体系（渗透/破解/逆向专用）

> 基于 BetWin4 泄露源码（C# .NET Core）+ PHP 代理模板（Diamond Bet System）双重分析
> 生成时间: 2026-07-14

## 一、BetWin CMS 的两种形态

BetWin CMS 实际是两套系统：

| 形态 | 技术栈 | 典型路径 | 用途 |
|:-----|:-------|:---------|:-----|
| **代理前端/登录面板** | PHP + Apache | `ag.domain.com/app/daili/` | 代理登录/管理界面 |
| **核心API聚合中台** | C# .NET Core (BetWin4) | `domain.com:8000/v1/...` | 游戏API聚合，商户管理 |

PHP 前端通常部署在 Cloudflare 后面，6+ 个后端 IP。.NET Core 后端可能在不同端口（8000/9000）。两个组件可能共享同一套 MySQL/Redis 数据库。

## 二、PHP 代理前端攻击面

### 系统识别
- 登录页 CSS 含 `bg_super_*` / `gs_bg_*` / `daili_bg_*` 背景图
- 登录表单 POST 到 `./login.php` 带 hidden 参数 `active=1`, `uid`, `langx=zh-tw`
- 版权: `© Copyright by Diamond Bet System Corporation`
- 错误消息含拼写错误: `"Plaese input username/passwd and try again!!"`

### 已知登录端点
```
POST /app/daili/login.php    → 代理登录（active=1, username, password, langx=zh-tw）
POST /app/member/login.php   → 会员登录（username, passwd）
POST /login.php               → 备用
```

### 已知防御
- WAF: Apache ModSecurity (406 拦截)
- Cloudflare DNS/CDN (6个A记录)
- Session: PHPSESSID (Max-Age=99999, 无HttpOnly/Secure)
- 前端 `is_login` 变量基于任意 Cookie 存在即显示 `'1'`（假阳性，不可信）

## 三、BetWin4 .NET Core 中台攻击面

完整源码分析见 `betwin-cms-source-code-analysis.md`

### 核心漏洞速查

| 漏洞 | 类型 | 详情 |
|:-----|:-----|:------|
| 硬编码数据库密码 | 配置泄露 | `uBW4 / HpTo4zqK2B7v6FQu` |
| 硬编码Redis密码 | 配置泄露 | `redis.bw4.com:6379` 同上密码 |
| 管理后台无验证码 | 认证缺陷 | `/Admin/Login` 可暴力破解 |
| Session无过期 | 认证缺陷 | 管理员Guid Session永不过期 |
| Guest接口 | 未授权访问 | `/Config/Init` 无需Token |
| 固定AES-IV | 密码学缺陷 | Pinnacle API: `RandomInitVector` |
| DES弱密钥 | 密码学缺陷 | AG API: 8字节DES密钥 |

### 数据库表结构
```
Site         → ID, Name, Prefix, Status, CreateAt, SecretKey(Guid), WhiteIP
Game         → Type(GameType枚举), Status, Setting(JSON)
SiteGame     → SiteID, Type, Rate, Status
SystemConfig → Type(ConfigType枚举), Value
SystemAdmin  → ID, UserName, Password, ...
User         → ID, UserName, Password, SiteID, ...
GameOrder    → ID, SiteID, Type, OrderID, Game, UserName, BetMoney, Money, ...
```

### 默认凭证
| 服务 | 凭证 |
|:-----|:-----|
| MySQL | `uBW4 / HpTo4zqK2B7v6FQu` |
| Redis | `HpTo4zqK2B7v6FQu` |
| 管理员 | 无默认账号（需暴力破解，无验证码） |
| 商户密钥 | `Guid.NewGuid()`（不可预测） |

## 四、关联资产发现模式

从目标站首页HTML提取关联域名的几个来源：

1. **图片/JS CDN** — `kfc.jfwdpc.com`, `bbc.xhrsa.com`, `mca.klssy.com`, `nxy.ycybbx.com`
2. **友情链接** — `6533388.com`, `9599wm.net`, `72886mm.com`, `9580.com`
3. **备案号/客服** — 底部ICP备案号
4. **后端IP** — 页面中的直接IP引用，如 `18.162.243.73:8888`
5. **DNS CNAME 链** — `www -> bbet888s.leboweb.com -> 3bc4306b.qcnodecd.com`
