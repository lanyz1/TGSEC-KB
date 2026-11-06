# 实战案例:小红书直播弹幕采集工具卡密绕过(2026-08 CTF)

目标: `小红书直播评论采集.zip`(459MB)→ Electron 应用 `小红书直播弹幕采集工具.exe`
任务: 绕过卡密验证直接登录进入。结果: 双击 `最终结果.exe` 直进,完全离线。

## 结构与指纹
- 加壳启动器 `小红书直播弹幕采集工具.exe`(40MB,VMProtect `.svmp1` 区段,strings 无输出,导入表仅基础 DLL)
- `main.dll`(176MB)= Electron 主二进制伪装(pefile 确认 PE32+ GUI x64 → 可改名 .exe 直跑)
- `resources/app.asar`(107MB)→ 核心业务,JS 明文
- `SunnyNet.dll`(49MB)由加壳 exe 动态加载,main.js 未引用(用途不明,不影响)
- `lic.ini` 仅 `[info] rtcs=0 auto_login=0`(无实际授权数据)

## 授权机制(main.js 逆向)
```js
if(process.env.XHS_ANON_LAUNCH_TOKEN!=="XHS_ANON_LAUNCHER_20260705_9F2D7C31")process.exit(0);
const fu = "http://49.233.127.44:13818";   // 授权服务器(腾讯云,HTTP明文)
async function So(e){                      // 卡密验证
  const n = await machineId();             // Windows MachineGuid
  return (await axios.post(`${fu}/api/check`, {key:e, machine:n})).data;
}                                          // code: 1=正常 2=将过期 -1/-2/-3=无效
setInterval(check, 8*60*60*1000);          // 8小时轮询,启动不立即触发
```
- 渲染进程仅在收到 `license-expired` 事件时锁定 UI;无 license_key 时 `Ao()` 返回 code:-2 → 发事件 → **但 UI 无 key 默认不锁定,8小时内直接可用**(软授权缺陷,无需任何操作即进)
- electron-store 无 config.json = 从未存过 key

## 三处修改(全部在 dist/main/main.js)
| # | 修改 | 效果 |
|---|---|---|
| 1 | 删除 `if(process.env.XHS_ANON_LAUNCH_TOKEN!=="...")process.exit(0);` | 双击直启 |
| 2 | `So(e)` → `return {code:1,msg:"ok",expire:"2099-12-31",days_left:99999,promote:""}` | 任意卡密永久授权,离线 |
| 3 | (兜底)fu → http://127.0.0.1:13818 | 无实际请求发出 |

## 关键命令
```bash
# 解包/重打包
npx --yes @electron/asar extract resources/app.asar app_extracted/
npx --yes @electron/asar pack app_extracted resources/app.asar
grep -c 'return{code:1,msg:"ok"' app_extracted/dist/main/main.js  # 验证进包

# 启动(绕过加壳启动器)
cp main.dll main.exe
XHS_ANON_LAUNCH_TOKEN=XHS_ANON_LAUNCHER_20260705_9F2D7C31 ./main.exe   # 改前
./main.exe                                                              # 删token检查后

# 验证
tail "$APPDATA/douyin-ip-query/app.log"   # Application started(日志目录名是旧项目名!)
tasklist | grep -i main.exe               # 4个进程=主+GPU+网络+渲染

# 打包提交(zip,1.2GB→451MB)
python3 - <<'EOF'
import zipfile, os
with zipfile.ZipFile('out.zip','w',zipfile.ZIP_DEFLATED,allowZip64=True,compresslevel=6) as z:
    for root,_,files in os.walk(src):
        for f in files: z.write(os.path.join(root,f), os.path.relpath(os.path.join(root,f),src))
EOF
# 然后 testzip() 验证完整性
```

## 踩坑记录
- 加壳 exe 改名(`最终结果.exe`)后**启动自校验失败,静默退出** → 弃用启动器,直接用 main.dll 改名 .exe
- 修改 asar 前必须先 `taskkill /IM main.exe /F`(文件占用导致重打包后仍是旧内容的风险)
- patch 报 node MODULE_NOT_FOUND lint 错误是预期(node 试图直接跑 electron 文件),不影响打包
- 假授权服务器方案(改 fu + 本地 HTTP 返回 code:1)也可行但需常驻服务;改 So() 更干净

## 交付物(CTF)
- `最终结果.exe`(Electron 主程序改名)+ 修改后 app.asar + 全部依赖 → zip
- writeup: 弱点分析表(客户端逻辑可篡改/令牌硬编码/HTTP明文/UI不强制)+ 修改对照 + 防御建议(asar签名校验/服务端鉴权/HTTPS+防重放)
