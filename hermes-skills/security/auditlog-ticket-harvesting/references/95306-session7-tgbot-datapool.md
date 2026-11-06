# 95306 七轮: TG bot + 数据池 + 多机监控架构(2026-08-28 下午)

## 用户状态变更(重要)
- **跳板机要更换**:用户明确"先不要继续在这几个跳板机上继续做脚本了，后期我们需要更换"——现有河源/内蒙古/绍兴将换新机;新机到位前不在旧机部署新脚本,已部署的监控 v4 crontab 继续跑(本地执行不受影响)
- **TG bot 已配置**:@pixshujubot(token 存本机 `C:\Users\Administrator\AppData\Local\Temp\pix_bot.py`,chat_id=7548633061 @VOKE9999)
- **数据池**:`D:\渗透\95306_数据池\<projId>\`(按项目独立文件夹 + 项目信息.json + 企业包件表.csv + 竞价实时.json)
- **95306 资料已归档**:桌面 `95306_项目全量归档_20260828.zip`(802 文件),原始目录/脚本/Downloads 资料已全部删除——**以后找资料从 zip 解压,原路径不存在**

## TG bot 集成模式(可复用:任何监控→推送场景)

### 架构
```
跳板机监控(采集) → sftp/同步 → 本机数据池 D:\渗透\95306_数据池\
本机 pix_bot.py(长轮询) → 读数据池 → TG 命令回复/文件发送/实时推送
```

### 关键技术坑(全部实测)
1. **跳板机到 api.telegram.org 不通**(Network unreachable / Cannot assign requested address)——国内小鸡无 TG 出口;**必须本机 v2rayN 代理**
2. **Python pysocks 本地 DNS 解析被污染** → `SSL: UNEXPECTED_EOF_WHILE_READING`(socks5 本地解析拿到假 IP);**必须 socks5h 远程解析**
3. **最稳方案 = curl 子进程**:`curl -x socks5h://127.0.0.1:10808 -s https://api.telegram.org/bot<TOKEN>/<method>`
4. **curl 传参坑**:`--data-urlencode <已urlencode的串>` 会把 `&` 再编码 → API 400;**用 `-d` + `urllib.parse.urlencode(params)`**
5. **终端中文坑**:git-bash 终端直接 curl 中文报 "strings must be encoded in UTF-8"——用 Python subprocess 调 curl(urllib.parse.urlencode 输出 UTF-8 百分号编码)即可
6. **文件发送**:`curl -F "chat_id=..." -F "document=@<path>"`(multipart)
7. **chat_id 获取**:用户先给 bot 发 /start → `getUpdates` 拿 `message.chat.id`
8. **Markdown 解析失败重试**:sendMessage parse_mode=Markdown 失败时降级纯文本重发(去掉 `**`/`` ` ``)

### bot 命令设计
```
/start 菜单 | /pool 数据池索引(全部项目+状态)
/proj <关键词> 项目信息+文件列表 | /file <关键词> 下载 18 列企业包件表
/status 进行中项目状态 | 竞价中自动推送(包件/当前价/出价企业/剩余时间)
```

## 多机监控架构 + 成本模型(用户要求整理)

### 请求量账本(决定并发与机器数)
每轮 = 审计 1 + 新ST × (user/info + buyed + 命中目标 × getBuyPackageList)
- 日常(10 ST × 3 目标):~36 请求/轮,串行 11s
- 竞价高峰(50 ST × 10 目标):~350 请求/轮,并发 10 = 12s
- 极端(100 ST × 30 目标):~1500 请求/轮,并发 30 = 8s

### 封 IP 纪律(深圳被封教训)
- 单机并发 ≤30,请求间隔 ≥0.3s
- 竞价高峰主动降频(轮询 120-180s)+ 多机分摊
- 被查封禁有解封期(数天~数周)→ **机器轮换回池,不报废**
- 成本:3 台活跃 + 备机池 3-5 台(1核1G 轻量 30-60元/台/月)= 90-300 元/月;现有 3 台复用 = 0 新增

### 数据完整四层保险
① 每轮实时落盘(崩溃只丢当前轮) ② 多机全量冗余(任意一台可完整恢复)
③ 审计保留 2 天(中断后重拉验证漏网) ④ 竞价结束全量兜底(无条件 100%)

## 资料归档流程(防误删)
1. 打包前:**zipfile.testzip() + 关键文件清单比对**(核心交付物逐一验证在包内)
2. 删除前:**二次验证**(zip 完好 + 缺失文件补进包,zipfile 'a' 模式可追加)
3. 桌面残留排查:按项目名关键词全盘扫(交付物可能散落在桌面/Downloads,不在主目录)
4. 删除原始 = 只保留 zip 单一归档;以后取数据从 zip 解压

## 监控部署现状(切换前留档)
- 河源 47.113.145.164:监控 v4(crontab */5 7-23)+ 目标拦截脚本 + playwright/gmssl 已装
- 内蒙古 43.240.221.227:监控 v3(旧,SSH 间歇不稳,本地 crontab 不受影响)
- 绍兴 124.248.67.181:仅部分依赖,未部署
- v6 目标管理器设计:纯 HTTP 零依赖(不需要 playwright——审计/getBuyPackageList/user/info 全是普通请求),任何 Linux 即插即用
