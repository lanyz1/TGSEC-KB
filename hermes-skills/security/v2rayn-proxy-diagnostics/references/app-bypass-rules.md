# 应用级代理豁免:指定程序直连不走 v2(2026-08-26 实战验证)

场景:让 WeGame/LOL(或其他国内程序)永久直连,不走 v2rayN 代理。
系统代理模式与 TUN 模式两种情况下均生效。本次操作 = 修改激活路由组,非 TUN 开关。

## 权威配置来源(重要)
- 路由规则唯一持久化位置:`guiConfigs/guiNDB.db` 表 **`RoutingItem`**(列:Id, Remarks, Url, RuleSet, RuleNum, Enabled, Locked, IsActive, ...)
- `RuleSet` 列 = **JSON 数组**,每条规则字段:`Id`(string), `Remarks`, `OutboundTag`, `Domain[]`, `Ip[]`, `Port`, `Network`, `Protocol[]`, **`Process[]`**, `Enabled`
- 激活的路由组:`IsActive=1`(本机当前 = "V3-绕过大陆(Whitelist)",Id=5502388336503853984)
- v2rayN 启动时从 db 加载路由组 → 生成内核配置;**退出时把内存配置回写 db → 改 db 必须在 v2rayN 关闭状态下进行,否则被内存覆盖**

## 规则顺序 = 先匹配先生效
xray/sing-box 顺序匹配,第一条命中生效。进程直连规则必须插在 RuleSet **数组最前面**(任何 proxy 规则之前),否则流量先撞上代理规则。

## 操作流程(已实战跑通)
1. 备份:`cp guiConfigs/guiNDB.db "guiConfigs/guiNDB.db.bak_$(date +%Y%m%d_%H%M%S)"`(guiNConfig.json 一并备份)
2. **先征得用户同意再停 v2rayN**(用户铁律:关/重启/杀进程前告知并获同意):
   `powershell -c "Stop-Process -Name v2rayN -Force"`(子进程 xray/sing-box 一起退)
3. 等端口释放:`netstat -ano | grep -E "10808|10814" | grep LISTENING` 无输出才安全
4. python 改 db(脚本见下):读激活组 RuleSet → json.loads → 新规则插最前 → json.dumps 写回 → assert 无重复 Id → 读回验证
5. 重启:`powershell -c "Start-Process -FilePath '<v2rayN.exe 绝对路径>'"`,等 10s
6. 验证:
   - 端口 LISTENING + 进程存活
   - 代理本体:`curl -s --proxy http://127.0.0.1:10808 -m 10 -o /dev/null -w "%{http_code}" https://www.google.com/generate_204` → 204
   - 直连正常:`curl -s --noproxy "*" -m 8 -o /dev/null -w "%{http_code}" https://www.baidu.com` → 200
   - db 读回确认新规则存在(权威验证,不必读内核运行配置)

## 改库脚本模板
```python
import sqlite3, json
db = sqlite3.connect('guiConfigs/guiNDB.db')
cur = db.cursor()
cur.execute("SELECT Id, RuleSet FROM RoutingItem WHERE IsActive=1")  # 激活组
gid, rs = cur.fetchone()
rules = json.loads(rs)
new_rules = [
    {"Id": "786729677092", "OutboundTag": "direct",
     "Process": ["wegame.exe","WeGameApp.exe","League of Legends.exe","LeagueClient.exe",
                 "Client.exe","CrossProxy.exe","TenioDL.exe","TPHelper.exe","TenProtect.exe"],
     "Enabled": True, "Remarks": "WeGame/LOL进程直连"},
    {"Id": "786729677093", "OutboundTag": "direct",
     "Domain": ["domain:qq.com"], "Enabled": True, "Remarks": "腾讯qq.com直连"},
]
rules = new_rules + rules                      # 插最前
ids = [r["Id"] for r in rules]
assert len(ids) == len(set(ids)), "重复Id!"    # Id 是 string,必须唯一
cur.execute("UPDATE RoutingItem SET RuleSet=? WHERE Id=?", (json.dumps(rules, ensure_ascii=False), gid))
db.commit()
cur.execute("SELECT RuleSet FROM RoutingItem WHERE Id=?", (gid,))
back = json.loads(cur.fetchone()[0])
print('规则数', len(back), '| 前两条:', [r.get("Remarks") for r in back[:2]])
db.close()
```

## 进程名匹配语义
- 规则里填**纯进程名**(如 `wegame.exe`)即可:xray 同时做完整路径匹配与 basename 匹配、不区分大小写;sing-box 端对应 `process_name`
- 不必填完整安装路径(路径随安装位置变化,且 xray 通配路径易错)

## 规则 Id 约定
- Id 是 string,不能与组内其他规则重复(脚本 assert 兜底)
- 用独立数字段(本机手动规则用 `7867296770xx` 段)避免与 UI 生成的雪花 Id 撞车

## 生效范围
- 系统代理模式(本机当前,TUN 关):走 WinINET/系统代理的游戏组件流量到 10808 后按规则 direct 放行;游戏 UDP 主流量本就不进 xray
- TUN 模式:全局流量进 sing-box,process_name 规则同样命中 → 游戏强制直连、对局 UDP 不走代理

## 坑
- git-bash 调 powershell 传 `$_` 会被 bash 展开 → 用单引号包 PowerShell 命令或改 python subprocess;中文 Windows 下 PowerShell 输出为 GBK,`subprocess.run(..., text=True)` 的 utf-8 解码会炸 → 用 bytes 输出或 `encoding='gbk', errors='replace'`
- 本机 `binConfigs/` 为空(TUN 关闭时),xray 运行配置 `-c config.json` 是相对路径、生成文件在临时目录——别指望读它验证,以 guiNDB.db 为权威
- `Client.exe` 进程名较泛(可能匹配其他软件的同名进程),但 direct 直连最坏结果 = 不走代理,国内环境无害;配 `qq.com` 域名兜底后更稳
