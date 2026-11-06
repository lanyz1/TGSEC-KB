<!-- archived from /root/.hermes/skills/security/resource-panel-unauth/SKILL.md on 2026-10-21 -->

---
name: resource-panel-unauth
description: "Use when 未授权资源/VPS管理面板：list泄露下游root密码、create批量造资源白捡。"
version: 1.0.0
---

> 归档卡：原目录 `/root/.hermes/skills/security/resource-panel-unauth`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/resource-panel-unauth/…')`，不要相对 `references/legacy/` 解析。

# 未授权资源管理面板（VPS/云资源中转站）

养号/云手机/博彩灰产系统背后常有一个**资源管理面板**（向 VPS 供应商下单建机的中转站），跑在应用层（Flask/Spring），与端口级未授权服务（Redis/Docker 那类）不同——它的 list 接口直接吐下游资源的**明文凭据**，create 接口能**滥用余额批量造资源**。

## 核心攻击链（白捡 root）

1. **`GET /<前缀>/account-info`** — 未授权返回账户：余额、真实姓名、内网 IP 段（`default_ip_range`）、phone/email、`affiliate_code`。
2. **`GET /<前缀>/list-vps`** — 未授权返回每台 VPS 的 **root 明文密码** → 直接 SSH 白捡 root，无需爆破。
3. **`GET /<前缀>/create-vps/<n>`** — 未授权批量创建 VPS（扣账户余额，每台 ~907 VND）→ 创建完成后 list-vps 又吐新 root 密码 = **可持续白捡 root 的摇钱树**。

**铁律：** 资源管理面板的 list/create 接口要先于爆破测——明文凭据直接 SSH，比硬刚认证墙快一个数量级。

**坑：** `create-vps/<n>` 里 `range(int(n))` + `time.sleep(120)` 是死循环式批量创建，n 给大（如 999）会一直扣余额连发下单 → 触发运营者告警 → 清场（删所有 VPS 的 authorized_keys、改密码、停 VPS、关面板端口），把你踢下去。滥用要克制：小批量 + 观察响应，拿到几台先收手，别一次性大 n。

## 用类型错误收割源码

- `create-vps/abc`（非数字）→ 视图里 `int("abc")` ValueError → Werkzeug debug 页泄露该函数完整源码：上游供应商 API 端点（`https://cms.<vendor>.com/api/v1/cshp-order/create`）+ 全局 token 引用（`Authorization: Bearer {token}`）+ data 构造（package_id/region_id/image_id/billing_mode）。
- 同机多个 Flask 应用（:8000/:7000/:10000）共用 machine-id + MAC，只是 username 不同 → 破一个 PIN 算法通用。

## 上游供应商 CMS 门户

- **先 curl `env-config.js`**：泄露 `REACT_APP_API_URL`、`REACT_APP_PANEL_URL`（面板 URL，如 whpanel.com）、recaptcha site key。
- **`main.js` 反混淆过滤框架库**：大 bundle（6.9MB 含 CKEditor）用 `grep -oE '/api/(v1/)?[a-z0-9/_-]+' main.js | sort -u | grep -viE 'ck-|ckeditor'` 滤掉样式噪音。高价值端点：`/api/v1/control/get-console-websocket`（VNC 控制台）、`/api/v1/db-details`、`/api/v1/cloud-servers`、`/api/v1/control/reinstall`。

## Laravel 门户（register + 邮箱验证）

- `POST /api/register` 直接成功（`User registered successfully`），但 login 前需邮箱验证（signed URL，需 Laravel APP_KEY 签名，难绕过）。
- **`POST /api/login` 响应差异 = 账号枚举 oracle**：`"Email chưa được đăng ký"`（未注册） vs `"Email hoặc mật khẩu không đúng"`（已注册密码错） vs `"chưa được xác thực"`（未验证）——三个不同 message 区分三种状态。

## 供应链要点

养号系统 → VPS 供应商 → 养号机 VPS，整条链面板都未授权/弱鉴权，任意一环失守都能横向白捡 root。挖到养号系统时，先找它的上游资源面板（内网端口扫 + 端口 banner 找 Flask/Werkzeug 面板）。
