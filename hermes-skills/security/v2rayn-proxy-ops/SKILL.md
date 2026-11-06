---
name: v2rayn-proxy-ops
description: "v2rayN代理运维: 节点故障诊断/中转账号轮换。触发: v2rayN, 代理没网, telegram断网"
version: 1.0.0
license: MIT
platforms: [windows]
---

# v2rayN Proxy Ops (Windows)

v2rayN 代理的故障诊断、中转节点账号轮换、路由规则(国内直连/direct 白名单)修改。

## Trigger
- v2rayN / 代理没网、Telegram 断网、国外流量全挂、国内正常
- 中转(socks5/HTTP)节点失效、换账号/轮换订单资源(xlsx)
- 用户提供中转资源表要求"接到 v2 里"
- 改路由规则: 国内直连 / 绕过大陆 / 给特定 IP/域名加 direct

## 环境 (本机)
- v2rayN 安装: `C:\Users\Administrator\Desktop\新v2包\v2rayN-windows-64-SelfContained\`
- 本地代理: `127.0.0.1:10808` (socks/mixed, xray 内核); 系统代理 = 127.0.0.1:10808
- 节点库: `guiConfigs/guiNDB.db` (SQLite, ProfileItem 表); 核心运行配置: `binConfigs/config.json`
- 路由规则: guiNDB.db `RoutingItem` 表 (V3-绕过大陆/黑名单/全局); 生效路由见 config.json `routing.rules`

## 诊断阶梯 (按顺序, 每步分叉)
1. **进程**: v2rayN.exe / xray.exe / sing-box.exe 是否都在
2. **端口**: `netstat -ano | grep 10808` 是否 LISTENING
3. **分流测试**(关键分叉):
   - 走代理访问国内 `baidu` → 200 = 路由规则正常
   - 走代理访问 `google`/`t.me` → **0.9s 快速失败** = 出站节点问题; 超时 = 节点彻底死
   - `curl --socks5-hostname 127.0.0.1:10808 <url>` 测 10808
4. **读节点**: `binConfigs/config.json` outbounds → address:port/user
5. **直测节点**(跑 `scripts/probe_relay.py HOST PORT USER PASS`):
   - TCP 通 + SOCKS5 握手报 "wrong version" = 不是 socks5(是认证代理隧道)
   - 无认证 HTTP 请求 → `407 Proxy Authentication Required` = HTTP 代理伪装层
   - 带认证 CONNECT → 二进制响应 + **"Connection timed out"** = **账号过期/订单失效**(节点没死, 认证后被拒)
6. **换新账号**: 用户 xlsx 资源 → 同 relay IP:port 的新订单账号 → 先 curl 验证再写入

## 账号轮换 (核心操作)
资源 xlsx 列结构: `出口IP地址 | 中转后代理地址 | 中转后端口号 | 中转后代理账号 | 中转后代理密码 | ... | 订单ID | S5明文完整格式`
- S5明文完整格式 = `socks5://user:pass@relay:port`
- **旧账号过期症状**: 认证后返回二进制假 "Connection timed out"(别误判节点死亡)
- **新账号验证**: `curl --socks5-hostname user:pass@relay:port https://api.telegram.org` → 302; `ipinfo.io/ip` = 资源里的出口IP
- **写入 v2rayN**:
  1. 备份 db: `cp guiConfigs/guiNDB.db guiConfigs/guiNDB.db.bak_$(date +%Y%m%d_%H%M%S)_manual`
  2. `UPDATE ProfileItem SET Security='新账号' WHERE Address='relay' AND Port=port`(Id 列 = 密码, 通常不变; Security = 用户名)
  3. 杀进程: `powershell -NoProfile -Command "Stop-Process -Name v2rayN,xray,sing-box -Force"`(git-bash 的 taskkill //F 无效!)
  4. 校验 db 未被 v2rayN 退出覆盖(它不全量写回, 手动 UPDATE 会保留)
  5. 启动: `powershell Start-Process v2rayN.exe -WorkingDirectory <dir>`, 等 ~8s
  6. 验证: config.json 已用新账号 → 走 10808 实测 google 200 / api.telegram.org 302 / 出口IP
- 验证清单和完整实操见 `references/relay-account-rotation.md`

## 路由规则 (国内直连)
- "绕过大陆(Whitelist)" 标准配置: `geoip:cn` / `geosite:cn` / `geoip:private` / `geosite:private` / 国内DNS → **direct**; 其余 → proxy
- 加 direct 白名单: v2rayN 界面 设置→路由设置→添加规则(outbound=Direct); 或改 guiNDB.db `RoutingItem.RuleSet`(JSON)
- 注意: 国内直连配好 ≠ 国外服务能通 —— Telegram 等必须走代理, 代理出口挂了国内直连救不了

## Pitfalls
- **过期账号返回假 "Connection timed out"**, 第一反应是节点死了, 实际换新订单账号即通
- 资源表里没有的节点别切(如 `q0_1746307169.ga6x.com:30801` 已废且不在当前资源)
- git-bash 里 `taskkill //F` 报 `Invalid argument` → 一律用 PowerShell `Stop-Process`
- v2rayN 运行中直接改 db 可以(UPDATE 立即落库), 但**必须重启 v2rayN** 才重新生成 config.json 生效
- 系统代理注册表: `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings` (ProxyEnable=1, ProxyServer=127.0.0.1:10808)
- 直连测节点时 `curl -v` 输出混二进制会被 grep 当 binary 截断 → 重定向到文件后 `grep -a`


---

## 外部库增量（2026-10-11 分享包）

## 自建节点替代失效机场 (首选修复路径)
机场/服务商整体故障时, 在客户端怎么调都没用 —— 用用户自有境外 VPS 自建一个节点, 几分钟就能恢复。
- 选机: 用 `~/.ssh` 里现成密钥能认领的境外机;**生产站可以用, 但只加独立端口监听**(8443/8444 之类), 绝不碰 nginx/业务配置;
  改前 `cp config.json config.json.bak`, 改后**必须 `xray -test -c` 过了再 restart**
- 装: 官方 zip 解到 `/usr/local/bin/xray`, 配置丢 `/usr/local/etc/xray/config.json`, systemd `enable --now xray` 常驻
- 参数: `xray uuid` 出 UUID; `xray x25519` 出 Private/Public key(**Private 给服务端, Public 给客户端**); shortId 取 8 位 hex;
  `dest`/`serverNames` 填一个真实可达的 TLS1.3 站当伪装站
- Reality 在高端口会打印 "Listening on non-443 ports may get your IP blocked by the GFW" 警告 —— 可接受, 能占 443 就优先 443
- **防火墙是必修课**: 少一条 `ufw allow <port>/tcp` 的表现是客户端**静默超时**(包被 DROP), 与"节点没起来"完全一样。每加一个端口就加放行
- **服务端 LISTENING ≠ 客户端可用**: 必须从客户端做 TCP connect + curl 全矩阵(出口IP / google 204 / youtube 200 / api.telegram.org 302)才算交付
- 汇报必须带撤销命令: `systemctl disable --now xray && rm -rf /usr/local/etc/xray /usr/local/bin/xray /etc/systemd/system/xray.service && ufw delete allow <port>/tcp`

## 链式代理 (两跳)
需要"用 A 机器的干净 IP 去用 B 节点"时(大陆源直连被拒 / 节点要求境外源 IP)。
- **服务端链(首选)**: 在中转机上加**第二个 inbound**(独立 UUID)+ 一个指向目标节点的 socks outbound + 一条 routing 规则(`inboundTag → outboundTag`),
  客户端看到的就**是一个普通节点**, 电脑/手机通吃。模板 `references/selfbuilt-node-and-chain.md`
- 客户端链(没有中转机时): xray outbound 里 `streamSettings.sockopt.dialerProxy = "<中转出站 tag>"`(headless 复测最方便);
  v2rayN 原生链是 `ProfileItem.PreSocksPort`(填前置节点本地端口), 字段少易配错, 有 VPS 就走服务端链
- 两跳会翻倍消耗中转机流量、RTT 叠加(CN→HK→US 首字节常见 2.4–3.8s) —— 汇报时说清楚
