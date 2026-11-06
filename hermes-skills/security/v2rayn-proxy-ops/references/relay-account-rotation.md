# 中转账号轮换实操 (2026-08-30 会话)

## 场景
Telegram 断网。v2rayN 进程/端口(10808)/系统代理全正常, 但走 10808 访问国外全 0.9s 快速失败, 国内 baidu 200。

## 定位链
1. `binConfigs/config.json` outbounds → socks 出站 `14.119.66.81:30901` + `q0_1746307169.ga6x.com:30801`
2. 两节点 TCP 都通, DNS 正常(`q0_1746307169.ga6x.com` → 59.38.127.246, 广东电信)
3. SOCKS5 握手 → `SOCKS5 reply has wrong version` → 不是 socks5
4. 无认证 HTTP GET → `HTTP/1.1 407 Proxy Authentication Required` → HTTP 代理伪装层
5. 带认证 CONNECT(python socket)→ 二进制 protobuf 风格响应, 内嵌 `Connection timed out` + 用户名 + 目标域名 → 认证通过但出口被拒
6. TLS 探测: 自签证书 `CN=QY, O=QY, qiyou.cn`(成都)→ 商业中转/机场隧道
7. HTTP CONNECT 认证失败时 curl 报 `Proxy CONNECT aborted` / exit 56

## 结论: 账号过期 ≠ 节点死亡
- 过期订单账号 → 认证后返回**假 "Connection timed out"**(节点入口活着, 但拒绝对该账号放行出口)
- 同 relay IP:port 换**新订单账号** → 立即全通

## 资源 xlsx 列结构 (s5中转资源_*.xlsx)
`出口IP地址 | 中转后代理地址 | 中转后端口号 | 中转后代理账号 | 中转后代理密码 | 备注 | 中转前代理地址 | 中转前端口号 | 中转前代理账号 | 中转前代理密码 | 更新时间 | 订单ID | S5明文完整格式 | S5Base64完整连接信息 | S5Base64账号密码 | (二维码x3)`
- S5明文完整格式: `socks5://user:pass@relay:port`
- 出口IP 用于验证: 走代理访问 `ipinfo.io/ip` 应等于出口IP 列

## guiNDB.db 结构 (v2rayN V7.13.2)
- 表: `SubItem`(订阅, 手动导入时 Url 为空) / `ProfileItem`(节点) / `RoutingItem`(路由) / `ProfileExItem`(测速)
- ProfileItem 关键列: `IndexId` / `ConfigType`(4=socks类) / `Address` / `Port` / `Id`(=**密码**) / `Security`(=**用户名**) / `Remarks`
- 改法: `UPDATE ProfileItem SET Security='新账号' WHERE Address='14.119.66.81' AND Port=30901`(密码 Id 通常不变)

## 重启 v2rayN 正确姿势
- git-bash 里 `taskkill //F //IM v2rayN.exe` → `Invalid argument/option - '//F'`(MSYS 路径转换坑)
- 正确: `powershell -NoProfile -Command "Stop-Process -Name v2rayN,xray,sing-box -Force"`
- 启动: `powershell Start-Process v2rayN.exe -WorkingDirectory <dir>`, 等 ~8s
- v2rayN 退出**不会全量写回 db**(运行中手动 UPDATE 的值在退出后保留)
- 注意: 杀进程前要用户明确同意(用户规则)

## 验证清单
1. `binConfigs/config.json` outbound user = 新账号
2. `curl --socks5-hostname 127.0.0.1:10808 https://www.google.com` → 200
3. `curl --socks5-hostname 127.0.0.1:10808 https://api.telegram.org` → 302(TG API 正常重定向)
4. `curl --socks5-hostname 127.0.0.1:10808 https://ipinfo.io/ip` → 出口IP(本例 72.245.135.169)

## 本例残留
- `q0_1746307169.ga6x.com:30801`(备注 123123)不在当前资源表, 仍是死节点, 别切过去
- 中转账号有订单有效期(本例 7/27 订单 8/30 旧号已过期), 到期同样症状 → 换新订单资源
