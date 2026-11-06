---
name: autojs-pro-crack
description: "破Auto.js系App: 卡密验证在云端JS脚本+指令下发。触发: Auto.js, 卡密破解, APK破解。"
---

# Auto.js Pro 魔改 App 卡密破解

针对基于 Auto.js Pro 二次开发的脚本工具 App(小苹果/引流/自动化类),卡密验证逻辑在**云端 JS 脚本**而非 Java/smali 层的破解方法论。

## 何时使用
- APK 解包后发现 `org.autojs.autojspro.*` 包 + `assets/project/*.js`
- App 启动拉取云端脚本(cloudRenew/renew 机制)
- 卡密/授权码验证 + 云端指令下发架构

## 第 1 步: 识别架构(决定逆向方向)
```bash
apktool d -f -o apk_src target.apk
# 特征判定(以下任一条 → 走本 skill,别浪费时间在 smali):
# 1. AndroidManifest 有 org.autojs.autojspro.v8.api.ui.V8ScriptExecuteActivity
# 2. lib/arm64-v8a 有 libroot_automator.so
# 3. assets/project/ 下有 main.js + cloudRenew.js(云端更新)
ls apk_src/assets/project/   # 业务全在这,smali 只是壳
```

## 第 2 步: 读本地 JS 找云端服务器
```bash
# main.js 通常只是启动器,启动调 cloudRenew
cat apk_src/assets/project/main.js
# cloudRenew.js 泄露云端控制服务器(核心情报!)
grep -oE 'http://[0-9.]+:[0-9]+[^"`]*' apk_src/assets/project/*.js
```
**cloudRenew.js 典型结构**: 检查版本 → 下载脚本列表 → 覆盖本地脚本。服务器 = 全部业务逻辑所在。

## 第 3 步: 云端服务器接口测绘(未授权!)
```bash
# 典型接口(Go 后端, /xxx.php 风格):
#   /mx/version.txt      版本号(明文)
#   /mx/scriptName.txt   脚本清单(明文!)→ 拿到全部脚本名
#   /renew/<name>.js     任意脚本未授权下载 ← 供应链面,直接拖全量源码
#   /activation.php?activation=<卡密>.txt&deviceCode=<设备码>  卡密验证(明文响应"激活成功"/"非法卡密")
#   /query.php?query=<卡密>.txt   卡密查询
#   /new.php  POST JSON            命令下发(核心!服务端 AI 决策)
#   /unbind.php /jiasuo.php /jiesuo.php /target/delete.php  卡密操作
python3 - <<'EOF'
import urllib.request
for p in ['/mx/version.txt','/mx/scriptName.txt','/renew/main.js','/notice.txt']:
    try:
        r = urllib.request.urlopen('http://IP:PORT'+p, timeout=10)
        print(p, r.status, r.read()[:200])
    except Exception as e: print(p, 'ERR', e)
EOF
```
**拖全部云端脚本**: scriptName.txt 列出名字后逐个 `/renew/<name>.js` 下载,重点 activation.js(验证)+ main.js(主逻辑)+ convention.js(核心自动化,常 20 万字符)。

## 第 4 步: 破解三步
1. **activation.js 恒真**(验证逻辑通常极简):
```js
// 原: o = http.get(".../activation.php?...").body.string(); if ("激活成功" == o) { 写入存储 }
// 改: 直接写入存储 + alert("激活成功(破解版)"),不调服务器
activation.activation = function(t, a) {
    a.put("shebeima", device.getAndroidId());
    storages.create("peizhi").put("shouquanma", t);
    storages.create("ticketKey").put("shouquanma", t);  // 双备份存储都要写
    alert("激活成功(破解版)");
};
```
2. **cloudRenew.js 禁用**(防云端覆盖破解):
```js
cloudRenew.cloudRenew = function () { return; };
```
3. **云端 main.js 落地本地**(本地 main 是空壳,完整逻辑在云端):
```
cp cloud_main.js apk_src/assets/project/main.js  # 用云端完整版替换
```

## 第 5 步(核心坑): 功能脚本依赖云端指令 → 必须 patch
**不 patch 会失败**: convention.js(核心自动化)调 `new.php` 拿任务指令,假卡密时服务端返回
`{"commands":[{"alert":"非法卡密","type":"alert"},{"type":"exit"}]}` → 弹窗+停止。
```js
// 1. alert case 改为忽略:
case "alert": log("云端指令(已忽略)"); break;
// 2. exit case 改为忽略(原逻辑写 runtimeStoppedByCloud + return):
case "exit": log("云端停止指令(已忽略)"); break;
// 3. 把 http.postJson(new.php) 改为本地指令生成:
//    - 本地初始化任务队列(从配置的 douyinhao 生成 renwuliedui/zongrenwushuzu)
//    - 返回本地指令数组 [{type:"jinruzhuye",...},{type:"sleep",sleep:3000},...]
//    - 上层只看返回值: "x"=网络失败, null=重试, 数组=执行
```
**判断是否还有服务器依赖**: `grep -oE 'http://[0-9.]+:[0-9]+' convention.js | sort -u` —— 剩余调用(如 OCR 服务/delete.php)通常被 try/catch 包住,不影响主流程。

## 第 6 步: 重打包 + 签名(避开 apktool 坑)
**apktool b 常见失败**: 中文路径 `failed to open directory` + `PNG signature` 错误(资源实际是 webp)。
**用 zip 直接重建(只改 assets,不动 res/dex,更快更稳)**:
```python
zin = zipfile.ZipFile(src, 'r'); zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    if item.filename in mods and os.path.exists(mods[item.filename]):
        zout.writestr(item, open(mods[item.filename],'rb').read())  # 替换
    else:
        zout.writestr(item, zin.read(item.filename))                # 原样
# 新增云端脚本(原 APK 里不存在,如 convention.js): 第二个循环 writestr
```
**签名**: `java -jar uber-apk-signer.jar --apk out.apk --ks crack.keystore --ksAlias crack --ksKeyPass 123456 --ksPass 123456`(自签 + v1/v2/v3,可直接安装)。

## Pitfalls
- **端口全 OPEN 是 TUN/防火墙假象** — 用 HTTP 真实请求区分(`GET /` 返回 HTTP 状态 = 真服务, EMPTY = 假)
- **卡密接口是参数化查询** — SQLi 通常不通,别浪费时间;卡密随机不可枚举
- **Go 后端错误消息泄露 struct**: `json: cannot unmarshal string into Go struct field newRequest.renwuliedui of type []int` → 直接用错误消息逆向参数类型
- **verification 必须看功能脚本是否调云端** — 激活绕过了但核心功能卡在云端指令 = 不完整破解(用户会要求完全破解)
- 诚实交付: 破解版能激活+主界面+本地循环,但本地模拟指令 ≠ 原版云端 AI 决策,行为可能有差异,如实告知

## 参考
- `references/xiaopingguo-promax-case.md` — 小苹果ProMax v1.4.1 完整案例(服务器接口表/指令系统/逐层 patch 记录)
