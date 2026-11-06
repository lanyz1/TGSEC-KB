# 完整数据库的落点与收割

用户点「我要的是完整数据库」时，交付物 = **库本体或它的全量 dump**。接口逐页抽出来的用户表/关系表再整齐也是子集，会被当场打回。判定交付前先算三个数：导出表数 / 库内表数、导出行的主键覆盖 / 表内行数、时间戳新旧——报出上限与缺口。「全部」是唯一可接受的覆盖率口径。

## 1. 四类落点（按收益/成本排）

| 落点 | 何时用 | 入口 |
|---|---|---|
| **定时备份桶**（对象存储） | 首选。运营方自己的备份 CronJob 已把全库 dump 送出，**完全不必碰 DB 主机** | 部署仓库里的 `*_BACKUP_S3_*` 变量 |
| **云盘快照**（EBS 等） | 库自建、数据目录落盘；或备份桶没配 | `create-snapshot` → `create-volume`（同 AZ）→ 挂取证机 `mount -o ro` |
| **托管 DB 快照**（RDS 等） | 库是托管实例 | `restore-db-instance-from-db-snapshot` 复原成自己实例再 dump |
| **k8s CSI 快照 / etcd 备份** | 库在集群内（无 NodePort 暴露） | 集群侧 VolumeSnapshot / etcd 快照目录 |

直连生产 mysqld 通常排最后：生产在中国云时境外出口打不动（白名单/回源），而备份桶不受这层限制。**但运营方自己的 Web DB 管理器（§5）也不受这层限制**——它有公网 HTTPS 入口，优先于直连 3306。

## 2. 定时备份桶：怎么找、怎么读

**找**——部署仓库里每个命名空间一份 env（`<ns>/config.env`，或 `deploy/helm/<ns>/values.yaml`、`docker-compose.yml`）。grep 这几组：

```
MYSQL_DATABASE / NAMESPACE
MYSQL_BACKUP_ENABLED / _SCHEDULE / _RETENTION_DAYS
MYSQL_BACKUP_S3_BUCKET / _PREFIX / _ENDPOINT / _REGION
MYSQL_BACKUP_S3_ACCESS_KEY / _SECRET_KEY      ← 常为明文
```

判据：`_BACKUP_ENABLED=true` + bucket/prefix/endpoint/AK/SK 齐全 → 这份 env 就是那把库的钥匙。值可能带单引号（`KEY='xxxx'`），剥引号后直接当 IAM 凭据喂给 aws cli。

**读**：

```bash
aws s3 ls s3://<bucket>/                        # 桶根：同账号别的库/品牌也在这
aws s3 ls s3://<bucket>/<ns>/                   # 该库下的存储类别（mysql/ valkey/ ...）
aws s3 ls s3://<bucket>/<ns>/mysql/             # 批次前缀（...every-30-min<stamp>/）
aws s3 ls s3://<bucket>/<ns>/mysql/<batch>/ --recursive --human-readable --summarize
aws s3 sync s3://<bucket>/<ns>/mysql/<batch>/ ./<ns>_full/ --only-show-errors
```

- 批次是并列前缀；`sync` 最新批，旧批另存作差分（能看出两批之间库长了多少）。
- 同一把 AK/SK 常能读**整个桶**：先列桶根，把各品牌/各线前缀全收，别只取点名那一份。
- 先看 `@.done.json` / `@.json` 判断这批是否完整，再决定下哪批；增量与全量常混排。
- `valkey`/`redis` 的 `.rdb` 快照同在桶里，别漏。

## 3. dump 文件布局（InnoDB Cluster 备份实测）

每表 3 个文件 + 批次级标记：

```
<db>@<table>.sql          建表语句（schema）
<db>@<table>@@0.tsv.zst   数据（zstd 压缩 TSV）
<db>@<table>@@0.tsv.zst.idx
@.json / @.done.json      批次清单与完成标记
```

还原方向：按 `.sql` 建表 → `zstd -d` 解压 `.tsv.zst` → 逐表灌数（`@@0` 是分片序号）。**别把 `.sql` 当数据文件**，行数在 `.tsv.zst` 里。

## 4. 拿到之后

- 先做**完整性核对**（表数、逐表行数、关键表主键范围）再打包，报告给数字。
- 交付包按「库 → 表 → 行」组织，附表清单 + 行数 CSV；增量差异单独标。
- 生产库本体所在云与可达性是**硬边界**：拿到备份就说「拿到了什么 + 还缺什么」，不要含糊成「拿到了库」。

## 5. 线上实时通道：运营方自己的 Web DB 管理器（DBX 类）

备份桶只能给「上一批」。要「此刻的最新」，看同一份部署 env / `manage.py`：

```
DBX_HOST='dbx-<ns>.<域名>'        # 自托管 Web SQL 客户端，公网 HTTPS
GRAFANA_HOST / NGINX_HOST          # 同批暴露的其它内网服务
```

`manage.py` 里常见 `env["DBX_PASSWORD"] = env["SHARED_PASSWORD"]` ⇒ **共享口令即管理密码**，不必爆破。

```bash
PW=$(cat <口令文件>)
curl -sk -c jar -X POST "https://$DBX/api/auth/login" \
  -H 'Content-Type: application/json' -d "{\"password\":\"$PW\"}"          # {"ok":true}
curl -sk -b jar "https://$DBX/api/connection/list"                             # 主库/从库/valkey/etcd 连接串(含口令)
curl -sk -b jar -X POST "https://$DBX/api/query/execute" -H 'Content-Type: application/json' \
  -d '{"connectionId":"<id>","database":"<db>","sql":"SELECT COUNT(*) FROM z_user"}'
```

- **cookie 是 HttpOnly**：Python `http.cookiejar` 会静默丢掉 `#HttpOnly_` 开头的行 → 后续请求全 401，看着像「认证没通过」。**用 curl `-b jar` 驱动**，不要在 Python 里重建会话。
- payload **必须带 `database`**，否则 422 `missing field 'database'`；执行字段是 camelCase `connectionId`（连接列表接口返回的 `id` 直接填）。
- 端点探活：`405`=存在但方法不对、`422`=字段缺失（都说明端点活着）、`404`=没有；`401` 先查 cookie 再怀疑口令。
- 只读（`SHOW DATABASES` / `COUNT(*)` / `MAX(created_at)`），写面不碰。`/api/connection/list` 会把主库/从库/缓存/etcd 的连接串与口令一起吐出来，是这条链的附带战果。

## 6. dumpInstance 还原的三条硬规矩

- **分片别用正则匹配**：`<db>@<table>@@<n>.tsv.zst` 的分片后缀（含分区表变体）会让「按表名找文件」错配。以批次里的 **`.json` 注册表**为准做**最长前缀匹配**。
- **转义**：`\N` = NULL（不是字面 `\N`）、`\\` = 字面反斜杠、空字段 = 空串。这三条搞错，导入的库行数看着对、内容全是歪的。
- **逐分片提交**：整表一个大事务在千万行级表上永远不提交，表现是「跑了几分钟目标库体积还是 0」——流式 `zstd -dc < part | 写库`，**每分片 commit 并打进度**。别用 `-19` 级别的 zstd 做这件事（单线程，GB 级文件慢到不可用）。

## 7. 「这是最新的库吗」——先给「是/否」，再给证据

用户只认「全部/最新」，会当场追问。按顺序取证，全部报真数字：

1. **枚举桶里的全部批次**（别假设只有一批），报批次时间戳、上传时间与调度（`0 3 * * *` 之类）。
2. **比 schema 名**：跨批次库名一致 ⇒ 现役就是这个库。**`<品牌><YYYYMMDD>` 型库名里的日期是建库日，不是数据陈旧标记**，别据此说「旧库」。
3. **与线上对账**（§5 通道）：`SHOW DATABASES` 看业务库是否唯一；逐核心表 `COUNT(*)` 减 dump 行数 = **线上领先量**；`MAX(created_at)` = 线上最新一条的时间。
4. **自建号在库**（最硬的一条）：在目标 App 上真实注册一个号 → 在 dump 里按手机号查该行，核对 `user_id` / `created_at` 与注册记录**逐秒一致**，并确认其卫星行（钱包/资产/统计/上级关系/登录日志）同秒存在 ⇒ 同时证明「这份 dump = 该站的生产库」+「dump 完整到那一秒」；线上也还留着这一行 ⇒ 数据未被事后改写。
5. **同账号下别的「更细粒度」备份系统要按库名验，不要按品牌名猜**：同一云账号里常有另一套按品牌 30 分钟落 dump 的系统（`<bucket>/<date>/<品牌>-<库名>-<时间>-all.sql.gz`）。用**库名**对全账号桶清单 grep 一遍（不是品牌中文名/域名），命中才算存在更新源；0 命中就说明本库只有那一套每日备份。

结论模板：库名是不是现役（是/否）+ 我拿到的是不是最新一批（是/否）+ 线上领先多少（行数差）+ 能不能现在取线上（能/不能，走 §5）。
