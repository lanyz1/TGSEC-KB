---
name: rest-authz-validation-order
description: Use when 用 400 判定 API 未授权前要先验校验顺序。
version: 1.0.0
tags: [api, authz, rest, wordpress, false-positive]
---

# rest-authz-validation-order — 400 不等于「权限已过」

## 核心事实

**很多框架里，参数校验跑在权限校验之前。** 这时「400 Missing parameter」只证明路由存在、schema 生效，**完全不能证明鉴权缺失** —— 有没有 `permission_callback` 都会回一模一样的 400。

只凭 400 报「未授权」= 假阳性，交付时会被自己推翻。实测：靠 400 判定 `POST /wp-json/elementor-one/v1/plugins` 未授权、准备装配插件，用合法参数复测直接回 **`401 rest_cannot_install_plugin`**，结论作废、当面纠正。

## 各框架顺序（先查再下结论）

| 框架 | 顺序 | 400 能当「权限已过」用吗 |
|---|---|---|
| **WordPress REST** | 路由 → `has_valid_params()`（400）→ `permission_callback`（401/403）→ 回调 | ❌ **不能**，反序 |
| Django REST Framework | 权限类 → serializer 校验 | ✅ 能 |
| Laravel | middleware → FormRequest 校验 | ✅ 能 |
| FastAPI | `Depends` 依赖 → 参数校验 | ✅ 能 |
| Spring MVC | 拦截器 → `@Valid` | ✅ 能（默认） |

不在这张表里的框架，**先构造一个「参数合法但必然被拒」的请求**看它回 400 还是 401，再决定怎么读信号。

## 铁证复测：全合法参数 + 零变更值

拿到 400 之后，唯一合法的定性动作是：**补齐所有必填参数（含枚举白名单的合法值），发一次，看它回 401/403 还是 200。**

为了不产生副作用，选**零变更值** —— 已经处于目标状态的资源：

```bash
# ❌ 什么都没证明（400 在权限检查之前）：
curl -s -X POST https://T/wp-json/elementor-one/v1/plugins \
  -H 'Content-Type: application/json' -d '{"slug":"zzz-not-a-plugin"}'
# → 400 rest_invalid_param

# ✅ 合法枚举 + 已安装且已启用 = 零变更：
curl -s -X POST https://T/wp-json/elementor-one/v1/plugins \
  -H 'Content-Type: application/json' -d '{"slug":"elementor","status":"active"}'
# → 401 {"code":"rest_cannot_install_plugin"}   ← 护住的，结案
```

**零变更值怎么选：** 装插件类 → 已装且已启用的 slug + 它当前的状态；配置类 → 传当前已有的值；删除类 → 传不存在的 id（若仍回 404 而不是 401，才说明权限已过）。找不到零变更值时，先用 `OPTIONS` / schema 确认必填项，再拿**最小的合法写入**换定性，并在报告里写清做过什么写入。

## 判读表

| 复测响应 | 结论 |
|---|---|
| 401 / 403（`rest_cannot_*` / `rest_forbidden` / `invalid_nonce` / `Sorry, you are not allowed`） | 已鉴权，**不是漏洞**，别写进报告 |
| 200 + 业务成功文案 | ✅ 真未授权写 |
| 500 + 堆栈 | 已过权限进到回调，✅ 真未授权（回调自己炸了） |
| 仍是 400 | 参数还没全合法 —— 继续补，**别下结论** |

`invalid_nonce` 的 403 也算护住：nonce 校验通常写在 `permission_callback` 里。

## 坑

- **schema 里的 `enum` 是白名单线索，不是漏洞线索。** 拿到枚举值要先想「能不能零变更地用它」，而不是直接当「可以随便装」。
- **同一批路由里出现两种响应（`claude`→400 / `cursor`→403）时，这个差异本身就是顺序证据** —— 非法值走参数层、合法值走到权限层。看到这种分层就别再猜了，按上表补值复测。
- **别把 WP 的结论套到别的框架上，也别把别人的套到 WP 上。** 顺序是每个框架的实现细节，逐次确认成本只要一个请求。
- 探测前先 GET 热身拿 cookie（WAF/反爬场景），否则 400/403 可能是边缘层给的，跟应用无关。
