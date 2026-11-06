---
name: lowcode-admin-rce-primitives
description: "二开后台文件写/执行原语体检: 配置写、插件安装。"
version: 1.0.0
license: MIT

---

# 低代码/二开后台的服务端文件写与执行原语面

触发: 二开后台, autoCode, 插件安装, setSystemConfig, 配置文件写, 文件写 getshell, 代码生成。

## When to Use

- 目标后台是**低代码/脚手架二开**(GVA gin-vue-admin、Vol.Core、RuoYi 二开、FastAdmin 等),
  且你已经拿到**后台登录态**(含超管),但还缺一个**服务端命令执行**的落点
- 你在 `sys_apis` 全量路由里看到 `/autoCode/*`、`/skills/*`、`/system/*Config*` 这类**非原生模块**
- 你拿到了"能写文件/能拉起进程/能生成代码"的接口,需要判断它到底能不能变成 shell

**核心判断:二开后台的价值往往不在"洞",而在"设计上就带的服务端能力"。**
二开加的每个模块都是一个"让服务器替你干活"的功能,把它们当攻击面逐个体检,
比在鉴权层硬磕提权省事得多。**前提是先把全量路由脱出来**(见 `lowcode-admin-data-exfil` 的导出模板链)。

## 原语体检表(按性价比排序)

| 原语 | 典型接口/字段 | 能拿到什么 | 落地判据 |
|---|---|---|---|
| **配置写** | `setSystemConfig` | 改存储路径/程序路径 → **任意目录任意内容文件写** | 响应回真实落盘**绝对路径** |
| **插件/包安装** | `installPlugin`(multipart) | 上传包 → 服务端解包并复制进 server/web 目录 | 报错里出现**服务器绝对路径** |
| **代码生成** | `createTemp` / `pubPlug` | 按模板把代码写进代码库;`pubPlug` 会**编译** | 目标目录真的出现生成物 |
| **AI 技能库** | `/skills/saveScript` 等 | 往技能目录写脚本/资源,可打包成 ZIP | ⚠️ 见"AI 面易误判" |

### 通用硬条件(先确认,省得白干)
- **配置写是两个字段的乘法**:一个"存储类型/开关" + 一个"路径"。只改路径不改开关,
  **文件不会落在你指定的地方**
- 上传接口**自动生成文件名**(`<md5>_<时间戳>.<ext>`),扩展名可控但**文件名不可控** ——
  想落成 `authorized_keys` 这类"必须叫某个名字"的文件,得再找重命名接口(`editFileName`)
  或换带 `fileName` 参数的接口
- 上传接口通常**信任扩展名并在元数据里标记**(实测 `.php` 直接被标成 `php`),扩展名不是障碍

## AI 面的易误判(重要,别把文件写当 RCE)

`/skills/*` + `/autoCode/*AI*` + MCP 服务这一族看起来很香(能建技能、写脚本、打包,甚至
`getTools` 列出 copilot/claude/cursor/trae/codex),但能不能执行取决于 **AI provider**:

```sql
SELECT provider, model, base_url FROM gva_ai_provider_configs;
```

- `openrouter` / `deepseek-*` / 其它**云 LLM API** → 服务端**只生成文本,不执行任何产物**。
  技能脚本写进目录就躺着,**这条路到此为止**,别再围着它绕
- 只有 provider 是**本地 CLI agent**(codex/claude 客户端装在同一台机上)时,才存在
  "提示词注入 → 本地 agent 跑命令"的可能;即便如此也要先确认 agent 真在服务端跑
- 那些 `copilot/claude/cursor/trae/codex` 工具名,常常只是**导给开发者拿进 IDE 用的产物**,
  不代表服务端会调用它们

**先查 provider 再投入**,一条 SQL 省掉几小时。

## 静默/合规纪律(这类原语全是"改配置/写文件",必须守)

1. **动手前先快照**:配置类接口都有读对端(`getSystemConfig`),**先读出来落盘**再改
2. **收尾逐项改回并回读验证** —— 不是"我改回去了",是**再读一次逐字段核对**。
   实测:把 `oss-type` 从 `aws-s3` 改成 `local`,会让他们后续上传从对象存储落到本地盘,
   不改回去就是真破坏
3. **写出去的文件要么清掉、要么内容严格无害化**(只写 `<?php echo "MARKER"; ?>` 这类自检串,
   绝不写真 webshell,直到能证明可执行)
4. **认领"能写文件"时就交代清楚它还不是 shell**,不要用"准 shell / 拿下"这类措辞

## 参数名枚举:靠校验报错逐级推进(通用,不限框架)

二开接口没文档,字段名靠猜是纯浪费。三招按序用:

1. **最小字段 + 逐级增补**:发空 body 看第一个必填项报错 → 补上 → 看下一个必填项。
   错误消息会一路变形(`技能名称不能为空` → `工具类型不能为空` → 成功),把字段名一个个逼出来。
   实测破出 `tool`+`skill`、`tool`+`skill`+`fileName`+`content` 全靠这招
2. **故意类型不匹配暴露 Go 结构体**:给字段喂错类型,报错会点名
   `json: cannot unmarshal array into Go struct field SysAIWorkflowSessionUpsert.title of type string`
   —— **一次拿到字段名 + 类型 + 结构体名**,再按结构体名推其余字段
3. **散弹式 body**:一次带齐 20 个候选字段名(同名不同大小写 / camelCase / snake_case),
   某次返回 `code:0` 或错误消息突变 = 命中。**命中后立刻单字段回归确认**

## 抓开源源码破专有接口(比猜快一个数量级)

二开接口闭源,但**底层框架是开源的**。**别猜校验逻辑,直接读源码**:

```bash
# 全文件树 → 按关键词筛路径
curl -s "https://api.github.com/repos/<owner>/<repo>/git/trees/main?recursive=1" \
  | python -c "import sys,json;[print(t['path']) for t in json.load(sys.stdin)['tree'] if '<keyword>' in t['path']]"
# 取单文件
curl -s "https://raw.githubusercontent.com/<owner>/<repo>/main/<path>"
```

- 代码搜索用 grep.app **网页版**;其 `/api/search` 需要 token,**直连常返回空响应,别在那耗时间**
- 实测收益:读出插件安装的 `strings.Split(path,"/")` + `pathArr[2]+"/"+pathArr[3] == "server/plugin"`
  判定 + `GVAPLUGPINATH = "./gva-plug-temp/"` 常量,才反推出包内条目名该长什么样

具体配方(接口、字段、源码片段、失败模式)见
`references/gva-config-write-and-plugin-install.md`。

## Pitfalls

- **报"格式不标准"≠ 没解包**:校验常**发生在解包之后**,包里文件其实已经落地。
  看到这类报错别急着换格式,先想清楚"它是不是已经写过了"
- **环境配置错不是手法错**:实测某部署 `AutoCode.Root` 指向的目录与进程实际 CWD 不一致,
  安装链恒定死在 `lstat .../gva-plug-temp/...: no such file`。
  **确认一次(重试一次排除竞态)就收手** —— 那是目标自己的部署缺陷,再怎么调包也过不去,
  继续试只是烧时间。**但报错里泄露的绝对路径是真收益,记下来**
- **`go:embed` 会把磁盘写废掉**:若前端资源被打进二进制,往"看起来是静态根"的目录写 `.php`,
  HTTP 取回只会拿到 SPA 的 `index.html`。**判据:任意不存在的路径也返回同一个 SPA = 资源是嵌入的**,
  这个目录写了也没用
- **写完必须取回执行结果才算数**:文件落盘(响应回真实路径)只证明"写",不证明"执行"。
  **验收标准是取回被执行的输出**,不是落盘路径
- 上传/注入类操作**会在目标留下对象**(模板、技能、上传记录),把清理写进收尾流程;
  注入类尤其要按命名前缀批量清并复核计数

## 关联
- `lowcode-admin-data-exfil`: 同族数据面(导出模板脱库、注入读原语、注入写任意表)
- `cn-admin-framework-pentest`: 国产后台家族总纲(用户自有)
- `rce-encyclopedia`: RCE 打法家族矩阵


---

## 外部库增量（2026-10-11 分享包）

## 另一族:自研 `apicode` 分发式低代码后台(lingx 族与同型)

不是每个低代码后台都长成 GVA/RuoYi(有 `sys_apis` 路由表 + 插件安装)。**另一族把全部功能塞进
一个 POST 端点,用数字 `apicode` 分发**:前端只跟一个 `/api` 说话,body 形如 `{"apicode":N,"cmd":"…"}`
或 `{"apicode":8002,"e":"<实体>","m":"grid",…}`。

- **判定指纹 = 请求体里的平台令牌字段**(如 `lingxtoken` 一类):拿这个串去 GitHub 搜,能直接定位
  产品族与其**公开前后端源码**(实测 `lingxtoken` ⇒ `lingxcom/tracseek` / `tracseek-web`),
  比黑盒猜 apicode 快一个数量级。
- ★ **认证载体可能是请求体字段而非头**:先在 axios 封装(`d-*.js`,搜 `setRequestHeader` 邻域)里找
  `xxx = sessionStorage.getItem(...)`。**默认它走 `Authorization` 只会拿到「无权限」,把活票读成权限不足。**
- ★ **`apicode` 数字 = 枚举 oracle**:报错分层(非数字 → Java `For input string`;数字但无租户 →
  `<n>接口未实现`)⇒ 别盲爆,先从 bundle / 浏览器 hook 抓真实值(量级可达 6 位)。
- ★ **有「通用实体查询」接口(`e=<表名>`,`8002` 型)时,权限校验是唯一的门**:拿到**任一**有权限的
  入口(菜单/元数据接口)就可能借它查任意表 ⇒ **优先测目标实体参数本身**,而不是穷举 ecode。
  但**判定必须夹对照**,见下方 Pitfalls。
- **平台元数据接口会顺手泄露字段名**:「获取属性与操作列表」+「获取表单配置」型接口会把**表结构
  (columns/queryFields)与前端组件路径**(`viewUri: <ns>/dialog/<Name>.vue`)一起吐。
  注意区分:**前者常只校验「入口 ecode 在不在本地图内」,不是全域存在性 oracle。**

深度配方(lingx 契约、分发器语义、`Utils.sqlInjection` 黑名单与排序字段 SQLi、后台会话换票链)见
`references/lingx-apicode-dispatcher.md`。
