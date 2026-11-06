# ag.61995q.com — BetWin CMS 渗透测试纪要

> 日期：2026-07-13 ~ 2026-07-14  
> 方法：黑盒低速探测（无有效账号、无爆破、无写入）

## 目标架构

```
ag.61995q.com
├── :443 (主站 - nginx → Apache)
│   ├── /index.php → iframe → /app/daili/index.php
│   ├── /app/daili/index.php → frameset → main_index.php?uid=9c97b145&langx=zh-tw
│   ├── /app/daili/main_index.php → 登录表单 (POST ./login.php)
│   └── /app/daili/login.php → 认证端点
│
└── :7777 (管理面板 - Apache)
    ├── /index.php → frameset
    │   ├── cl/index.php?module=System&method=first (公开)
    │   ├── cl/upupFlash.php (公开，Flash 集成)
    │   └── refresh.php (公开，自动刷新)
    ├── /cl/index.php?module=X&method=Y (路由系统)
    ├── /m/ → React SPA 移动端 (会员注册/登录)
    │   ├── /m/signup → 注册页
    │   ├── /m/login → 登录页
    │   └── /m/register/ → 注册别名
    ├── /api/ (403 — 存在但禁止)
    └── /api/Public/main/index.php?service=X.Y (注册API)
```

## CMS 识别

- **名称**: BetWin (biying / 必赢) 代理博彩管理系统
- **模板路径**: `tpl/biying/`
- **CDN**: `kfc.jfwdpc.com/1/cl/tpl/biying/` (主 CDN), `nxy.ycybbx.com/1/cl/tpl/biying/` (备用)
- **关联域名**: 9580.com, 9581.com, 95zz.com
- **jQuery 版本**: 1.8.3 (已知 XSS CVE)
- **客服系统**: `vue.livehelp100service.com` (siteId=65002347)
- **支付渠道**: ABPAY, QTPAY, OBPAY, USDT

## 三级管理员体系 (CSS 暴露)

从 `login.css` 的背景图目录名直接推断：

| CSS 资源路径 | 管理员等级 |
|---|---|
| `images/admin/newLogin/bg_super_*.jpg` | **超级管理员** |
| `images/admin/newLogin/gs_bg_*.jpg` | **公司/股东** |
| `images/admin/newLogin/daili_bg_*.jpg` | **代理** |

## 登录端点详情 (443)

**URL**: `POST https://ag.61995q.com/app/daili/login.php`  
**登录失败响应**: 200 / 158 字节 — `alert("LOGIN ERROR!! \nPlaese check username/passwd and try again(1)!!")`  
**参数缺失响应**: 200 / 142 字节 — `alert("Plaese input username/passwd and try again(2)!!")`

### 完整参数字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| username | text | — | 用户名 (maxlength=16) |
| password | password | — | 密码 (maxlength=16) |
| uid | hidden | (空) | 访客标识，由 main_index.php 生成 |
| langx | hidden | zh-tw | 语言 |
| active | hidden | 1 | 权限级别（仅前端使用，服务端忽略） |
| Submit | submit | 登&nbsp;&nbsp;入 | 提交按钮 |

### 参数测试结论

- **active 参数**: 23 个变体全部返回 SHA256 与基线一致 → **服务端忽略**
- **SQL 注入**: 三字段均无时间/布尔差分 → **无明显注入点**
- **弱口令**: 常见组合全部失败

## 移动端注册 API (7777)

### API 端点

| 服务 | URL | 方法 | 说明 |
|:-----|:----|:-----|:------|
| Server.GetCompany | `/api/Public/main/index.php?service=Server.GetCompany` | POST | 获取配置(含 client_id) |
| User.isRegister | `/api/Public/main/index.php?service=User.isRegister` | POST | 检查用户名 |
| User.Register | `/api/Public/main/index.php?service=User.Register` | POST | 注册新用户 |

### 已知参数

| 参数 | 必须 | 说明 |
|:-----|:-----|:------|
| `website` | ✅ | 租户标识 — 期望值为 `location.host` (如 `ag.61995q.com:7777`) |
| `client_id` | ✅ | 32+ 字符，从 GetCompany 获取 |
| `username` | ✅ | 4-12位小写字母数字 |
| `password` | ✅ | maxLength=12 |
| `agentid` | ✅ | 推荐人ID |
| `uname` | ✅ | 真实姓名 |
| `code` | condition | 图形验证码 |
| `ip` | ✅ | 客户端IP |
| `uid` | ✅ | MD5(password+username+client_id+website+ip) |

### `website` 参数枚举结果

所有尝试的域名都返回 416 "请求的website不存在"：
```
ag.61995q.com / ag.61995q.com:7777 / 9580.com / 9581.com
95zz.com / ag.5911x.com / kfc.jfwdpc.com / localhost
34.80.211.95 / 34.80.211.95:7777 / 1 (数字ID)
```
**结论**: `website` 是需要数据库配置的租户标识，黑盒无法猜测。

### client_id 验证

```json
{"ret":400, "msg":"client_id.len应该大于或等于32, 但现在client_id.len = 1"}
```
→ client_id 是 MD5/UUID 格式 (32+ 字符)

## WAF 特征

### 双层防护架构

| 层 | 位置 | 特征 |
|----|------|------|
| L1: 路径黑名单 DROP | 反向代理/IPS | TLS 连接直接关闭，000 响应 |
| L2: ModSecurity 406 | Apache | Apache 默认 406 页 (157 字节) |

### 触发 406 的 token

| Token | 触发? | 备注 |
|-------|-------|------|
| `'` (单引号) | ❌ | 允许 |
| `OR 1=1` | ✅ | 含空格+数字模式 |
| `OR/**/1=1` | ❌ | **注释绕过有效** |
| `OR/**/SLEEP(` | ❌ | **注释绕过有效** |
| `../` | ❌ | 但 nginx 会 404 |
| `../../etc/` | ✅ | 路径遍历+系统路径 |
| `EXTRACTVALUE` | ✅ | 报错注入函数 |
| `%2527` (POST body) | ❌ | 不触发但也不解码（PHP一次解码） |

### 触发 DROP (000) 的文件

| 路径 | 行为 | 推论 |
|------|------|------|
| `/cl/phpinfo.php` | TLS 连接终止 | 文件存在，路径黑名单 |
| `/cl/config.php` | TLS 连接终止 | 同上 |
| `*.zip` / `*.sql` (部分) | TLS 连接终止 | 备份/导出黑名单 |

所有绕过尝试均无法读取这些文件。

## Cookie 与 Session 行为

| Cookie | 作用域 | 效果 |
|--------|--------|------|
| PHPSESSID | 443 | 任何 PHP 请求自动设置。即使登录失败也会生成。**不能**用于 7777 认证 |
| Example_Session | 7777 | 首次访问 7777 时设置。能使 System/first 显示 `is_login='1'` |
| page_site | 7777 | 记录当前页面模块名 |

**关键发现**: 443 和 7777 的 Cookie **不互通**。

## 模块/方法枚举结果 (7777)

| 状态 | 路由 | 说明 |
|------|------|------|
| ✅ 200 (有内容) | `module=System&method=first` | 唯一的公开页面 |
| ✅ 200 (空) | `module=System&method=phpinfo` | 方法存在但返回空 |
| ❌ "尚未登录" | 其他所有 module+method 组合 | 受保护 |
| ✅ 200 (空) | `cl/upupFlash.php` | Flash 集成文件 |
| ✅ 200 (空) | `refresh.php` | 自动刷新页 |
| ✅ 403 | `/api/` | 目录存在 |
| ✅ 405 | `/m/api/register` | 注册 API 端点存在 |

## 未测试的方向

1. **真实账号测试** — 如有任何级别账号，可做登录后的横向/纵向越权
2. **CDN 侧翼扫描** — `kfc.jfwdpc.com` 可能存在其他客户实例泄露
3. **Flash 跨域攻击** — `crossdomain.xml` 通配策略 + `upupFlash.php`
4. **全端口扫描** — 本测试仅限 443 和 7777
5. **关联域名注册测试** — 9580.com / 9581.com / 95zz.com 可能配置了自助注册
