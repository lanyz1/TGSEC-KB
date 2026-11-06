# wukong-chat 破解版重打包排障实录(2026-08-09)

## 场景
wukong-chat v3.1.7 破解版(Electron)启动即崩。日志:
```
[ERROR] selectList:Cannot read properties of null (reading 'query')
[ERROR] selectAllHasList:Cannot read properties of null (reading 'query')
[ERROR] selectPage:Cannot read properties of null (reading 'queryWithAttach')
```

## 根因链
1. 之前用散件(只改了一个 main 文件)重打包 app.asar
2. 结果 `resources/app.asar` = 14.8MB(原始 37.6MB),**node_modules 全丢**
3. worker 线程 `new MultiDBManager(dbPath,...)` → `import Database from "better-sqlite3"` 失败 → dbManager = null
4. 所有 SQL 调用 `this.dbManager.query(...)` → null 解引用崩溃

## 关键诊断命令
```bash
# 对比大小(丢包信号)
ls -la resources/app.asar resources/app.asar.bak
# 14.8MB vs 37.6MB = 明显丢包

# 检查 node_modules 是否打入
npx --yes @electron/asar list resources/app.asar | grep -c "node_modules"
# 0 = 丢包

# 检查 crack 标记(extract-file 可能输出 0 字节!用完整 extract)
npx --yes @electron/asar extract resources/app.asar <tmpdir>
grep -c "cracked-wukong-token" <tmpdir>/dist-electron/main-BFxNbqFK.js
# 0 = 没打补丁; 2 = 补丁在
```

## 正确修复(实测通过)
```bash
cd D:/渗透/wukong
cp resources/app.asar resources/app.asar.nocrack   # 留底
npx --yes @electron/asar pack asar_extracted resources/app.asar \
  --unpack-dir "{**/*.node,node_modules/@img/sharp-win32-x64/**,node_modules/better-sqlite3/**}"
```
- 打包源必须是**完整解包目录** `asar_extracted/`(163MB,含 node_modules + 已 patch 的 main-BFxNbqFK.js)
- 结果: 120MB,6927 个 node_modules 文件,crack 标记 2 处

## 验证链
1. `npx @electron/asar extract resources/app.asar <tmpdir>` → grep crack ≥1 ✅
2. `ls <tmpdir>/node_modules | wc -l` > 0 ✅
3. 启动 `wukong.exe` → 5 个 Electron 进程存活 ✅
4. `Get-Process -Name wukong | Where MainWindowTitle` → 「悟空聊天」✅
5. 日志时间戳停在修复前(无新报错)= 成功 ✅

## 注意
- package.json `main: dist-electron/main.js` 是 stub(282B,只 re-export `M,R,V`),真逻辑在 `main-BFxNbqFK.js`(2.2MB,hash 文件名)— patch 目标是 hash 文件
- 用户数据配置 `%APPDATA%/wukong-chat/config.json` 预置 `cracked-wss-token` / `backaddress: http://127.0.0.1:81` 免登录直进主界面
- npx 在 python subprocess 里找不到(FileNotFoundError WinError 2),必须在 bash 终端跑
