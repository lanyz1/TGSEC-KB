---
name: electron-app-source-recon
description: Electron 应用源码深挖与复刻。触发 Electron 源码分析、复刻国产软件、全量源码走读。
---

# Electron 应用源码深挖/复刻(脚本化全量走读)

用于「把一套 Electron+Vue 软件源码挖到底,生成可复刻施工图」——页面/API/主进程/数据库/协议全链路映射。实战:悟空聊天 wukong-chat v3.1.7(63 页面/46 表/366 后台 API)。

## 触发条件
- 目标含 Electron 主进程 + Vue/React 前端 + 本地数据库(如 MultiDBManager/SQLite)
- 需要 1:1 复刻 / 理解全功能实现 / 审计攻击面
- 有完整源码目录(asar 解包后 / 源码包)

## 四层架构(先画这个)
```
前端 Vue3(src/views, N 页面) → src/api/*request.ts(window.ipcRenderer.invoke)
→ Electron 主进程(main.ts IPC handlers)→ 分发器(如 CommonInterceptor, if-else/switch)
→ Service 层 → 本地 SQLite(表清单)+ 远端服务器 + 第三方官方 API
```

## 脚本化提取流程(每步生成文档素材)

> 直接跑 `scripts/source_map.py <源码根目录>` 一键输出: 页面映射/IPC/分发器 URL/数据库表/taskType/WS cmd 六大类(实测 wukong: 63 页面/14 handlers/82 URL/46 表/6 cmd)

### 1. 页面→API 映射(脚本批量)
- 遍历 src/views/*.vue: 提取 `import ... from '...api/xxxrequest'` → 得到每个页面用的 API 模块
- 记录每个 vue 行数(核心页面按行数优先走读: >800 行的就是核心功能)

### 2. API 层→IPC
- 遍历 src/api/*.ts: 提取 `invoke('localRequest2','模块','方法')` → 得到模块名(如 letterTask/agent)
- 主进程 main.ts: `ipcMain.handle('localRequest'...)` 列表

### 3. 分发器全量提取
- CommonInterceptor 类: 正则 `url=="xxx"` 提取所有分支 → 82 个 URL 就是完整操作清单
- process2 模块化分支: `case "模块"` 提取
- 每个 URL 后 220 字符内找 `new XxxService` 确定底层服务

### 4. 数据库表(一键提取)
- MultiDBManager.ts: 正则 `CREATE TABLE (IF NOT EXISTS )?([a-z_.]+)` → 完整表清单(46 表)
- 每张表的功能从 Service SQL 推断(如 pm_proxy_info = 代理池)

### 5. 业务枚举(全局 grep)
- `taskType\s*[:=]\s*(\d+)` 全 src 提取 → 任务类型表(如 0普通/9强私/10群组)
- WS 协议 cmd: 正则 `cmd\s*[:=]\s*(\d+)|key:"cmd",value:"(\d+)"` + 上方方法名 → cmd 映射
- 注意: protobuf 生成的 im_proto.ts 里 cmd 是 case 标签不是常量;真实 cmd 在 wss/*Util*.ts

### 6. 核心链路走读(挑核心页面)
- 登录: handleLogin → 接口/加密/存储
- 消息: handleSend → `window.ipcRenderer.send('ws-send',...)` → worker → WS
- 任务: insertLocal → beginTaskAPI → worker 线程池
- 关注 AI/代理/翻译等特殊模块

### 7. 生成两份文档
- 主文档: 架构图/IPC/分发器/页面映射/数据库/链路/复刻要点
- 补充文档: 全页面函数清单/taskType/cmd/模块方法

## 关键陷阱
- **懒加载 chunk**: 主 bundle 只有框架 API,业务 API 在按路由懒加载的子 chunk(assets/xxx-8hash.js)→ 从主 bundle 提取 chunk 名批量下载再 grep
- **API base 是变量拼接**: `${l}/api/xxx` — base 来自 SSR payload(window.__NUXT__ / _payload.js)或 window.gameTab 配置,不在 JS 常量里
- **nginx SPA 回退**: 所有未知路径返回 index.html(200 HTML)→ 路径探测必须区分「返回 HTML」vs「返回真实内容」
- **页面映射用 import 语句**比搜函数调用可靠(vue 的 api 都走 import 的 request 封装)

## 复刻要点(从文档直接落)
- 客户端源码原封不动,改 common/constants.ts + getStore 返回真实 token
- 后端: 60 业务端点 + 46 表; 签名服务 Node 实现(AES 加密 queryStr → WS 头)
- 风控: 照搬 ProxyService+IPService+SingBox(代理池 + 账号绑定 + TUN 分流)
- 参考产物: D:\\渗透\\wukong_src\\源码深挖文档.md / 源码深挖补充.md

## 破解版重打包与启动排障(asar patch 回写)
> 破解 = patch 解包后的 main 文件(如 dist-electron/main-*.js 伪造登录 API + getStore 假 token),再重打包成 app.asar 替换。启动崩了先按此排查。

### 症状 → 根因速查
- 崩溃 + 日志 `selectList:Cannot read properties of null (reading 'query')` / dbManager null
  → **重打包时 node_modules 丢了**: worker 线程 require better-sqlite3 失败 → MultiDBManager 是 null。
  检查方法: `npx @electron/asar list resources/app.asar | grep -c node_modules`;对比原始 asar 大小
  (原始 37MB vs 残次 14.8MB = 明显丢包)
- 启动后行为=原版(还能登录作者服务器/验卡密)→ **crack patch 没打进去**:
  `npx @electron/asar extract-file` 提取 main 文件 grep 标记;注意 extract-file 输出到 stdout 时可能返回 0 字节(工具怪癖),**用完整 extract 到目录再 grep 更可靠**

### 正确重打包命令(实测通过)
```bash
cd <app目录>
npx --yes @electron/asar pack asar_extracted resources/app.asar \
  --unpack-dir "{**/*.node,node_modules/@img/sharp-win32-x64/**,node_modules/better-sqlite3/**}"
```
- **必须 --unpack-dir 保留 native 模块**(*.node → app.asar.unpacked/),否则 Electron 加载不了 better-sqlite3/sharp
- asar_extracted 必须是**完整解包**(含 node_modules),不是只改一个文件的散件;散件重打包 = 丢 node_modules
- 打包前 `cp resources/app.asar resources/app.asar.bak` 留底
- package.json 的 `main` 常是 stub(`dist-electron/main.js` 只 re-export `M,R,V`),真正的逻辑在 `main-<hash>.js` — patch 目标要打 hash 文件,stub 不用动

### 验证链(启动前必做)
1. `npx @electron/asar extract app.asar <tmpdir>` → grep crack 标记(如 `cracked-wukong-token`)≥1
2. `ls <tmpdir>/node_modules | wc -l` > 0; `.node` 文件在 app.asar.unpacked 里
3. 启动后: 进程存活 + `Get-Process -Name <app>` 有 MainWindowTitle + 日志无新报错(错误日志时间戳停在修复前 = 成功)
4. 用户数据配置(如 %APPDATA%/<app>/config.json)预置假 token 可免登录直进主界面

### 原版/破解版一键切换(用户常要求)
同一安装目录保留多份 asar 改名切换(2026-08 wukong 实战):
```bash
# 切换前先杀进程(用户同意后): Get-Process -Name wukong | Stop-Process -Force
mv resources/app.asar resources/app.asar.cracked   # 当前版存为带标记名
cp resources/app.asar.bak resources/app.asar       # 换另一份生效
# 重启 exe → Get-Process 有 MainWindowTitle = 成功
```
- 命名规范: `app.asar`=当前生效; `app.asar.bak`=原始未破解(~37MB); `app.asar.cracked`=破解完整版(~120MB 含 node_modules); `app.asar.nocrack`=残次重打包(~15MB,不可用留证)
- **大小一眼判断版本**: 原版 ~37MB / 破解完整版 ~120MB / 残次版 ~15MB
- 切回原版后程序走真实验证(验卡密/连作者服务器);切回破解版恢复免登录

### 员工账号密码表 ≠ 可直接登录(重要!2026-08 wukong 实测)
后台 API 拉到的员工表(如 `/api/staff/list` 返回 `passwd` 列)里那串 Base64 是**服务端加密存储**(如 AES-128-ECB,客户端无解密 key),不是明文密码——直接拿它当密码登录 100% 失败,也别浪费时间爆破哈希算法(非标准 MD5/SHA,直接解密是死路)。

**正确接管路径(实测全通)**:
1. 登录**管理后台 Web 面板**(常有独立域名/IP + 验证码,如 wukong 的 43.130.37.129,admin/admin + ddddocr 破验证码)
2. 从管理后台前端 chunk 挖员工管理 API(如 `staffList-163e3955.js` 里 `POST /staff/resetPwd`),**读源码拿确切参数格式**——wukong 是 `{tuid, password, passwordok}` 三字段,少一个就 500 内部错误
3. `POST /api/staff/resetPwd`(带管理 token)改任意员工密码 → 返回 `{"code":200,"msg":"更新成功"}`
4. 用 员工账号/新密码 登录客户端后端 API → 200 + JWT
- 陷阱: `/staff/save` 虽返回"保存成功"但 **password 字段不生效**(只存账号资料),改密必须走 resetPwd;resetPwd 的 500 内部错误 = 参数格式不对(看前端 chunk 的提交对象,不是猜)
- 陷阱: 部分后端接口响应整体 AES 加密(如 stafflogin 响应用 key=`8Y69AIO8ATqOs0bwt8C+Jw==` 解密),探测接口时先判断 `b.startswith('{')` 否则先解密再读

## 网页端 = 管理后台公网版(高价值横切面,2026-08 tk_wu 实测)

国产软件常带一个**公网 Web 管理后台**(与桌面版共享同一后端/服务器),`tk_wu.sswhgame.com`(wukong 网页端)就是典型:
- **同服务器同后端**: tk_wu.sswhgame.com → 43.130.37.129 = 桌面版管理后台 IP;nginx 直连无 CDN;桌面版渗透拿到的管理 token 在网页端直接通用
- **前端即 admin bundle**: 983KB 单 bundle `/assets/index-<hash>.js` + 138 个懒加载 chunk;前端 axios baseURL 写死 `http://127.0.0.1:81/api`(Electron 本地代理模式,Web 版走同源)
- 菜单全景: 数据统计 / 账号列表 / 任务管理 / GPT配置(智能体)/ 员工管理

### 网页端高价值数据接口(带管理 token)
- `GET /api/account/list2` → 52 个 TikTok 账号**完整凭据**(cookie/xtttoken/sessionid/wcookie/password/deviceInfo/region)🔴
- `GET /api/account/accountList` → 49 账号(同凭据,字段更全)
- `GET /api/agent/list` + `/api/agent/detail?tuid=N` → AI 引流智能体剧本 + **DeepSeek extApiKey**
- `GET /api/staff/list` → 员工表(AES passwd 哈希)
- `GET /api/accountGroup/groupAll100` → 运营分组
- 写接口(account/save、userinfo/resetPwdChild)参数不对返回 500,须从 chunk 提取确切 payload

### gzip 无头响应坑 ⚠️(多处命中)
部分接口(如 `/api/account/accountList`)返回 **gzip 压缩体但无 Content-Encoding 头**(curl 显示乱码 `\x1f\x8b...`)。必须手动检测解压:
```python
raw = resp.read()
if raw[:2] == b'\x1f\x8b':
    raw = gzip.decompress(raw)
```

### 管理后台完整 API 字典(88 个,chunk 批量提取法)
从业务 chunk 批量提取:`/account/list2 /account/save /account/deleteBatch /agent/list /agent/detail /agent/save /character/profile/* /cloud/task/* /conversation/channel/task/* /edevicelist/* /userinfo/getUserListEx /userinfo/resetPwdChild /staff/list /staff/resetPwd /search/search /receive/send/account/*` 等
提取法: 主 bundle 正则 `["'`](?:\./|assets/)?([a-zA-Z0-9_-]+-[a-f0-9]{8})\.js["'`]` 拿全部 chunk 名 → 批量下载 → 正则 `["'`](/[a-zA-Z0-9_/${}.-]{3,80})["'`]` 过滤业务关键词

