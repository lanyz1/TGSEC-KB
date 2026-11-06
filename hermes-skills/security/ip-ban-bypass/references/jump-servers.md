# 用户提供的渗透跳板资产(2026-09,OKPay 实战验证)

用户提供的 4 台电信跳板(换出口绕过目标 IP 风控用):

| 名称 | IP:端口 | 账号/密码 | 系统 | 状态 |
|---|---|---|---|---|
| 深圳电信 | 103.109.21.198:22 | root / 3VUe9OjleEss | ubuntu22 | ✅ 可用(主用,负载低) |
| 内蒙古电信 | 43.240.221.227:22 | root / vLAZ5fL4Zzfo | ubuntu24 | ✅ 可用 |
| 绍兴电信 | 124.248.67.181:22 | root / [REDACTED] | ubuntu24 | ✅ 可用 |
| 宁波电信 | 110.42.103.114:56102 | root / [REDACTED] | ubuntu24 | ✅ 可用(2026-09 更新密码,旧密码 3KPtV1vx 已失效) |

## 用法(OKPay 实战验证全流程)

1. 本地起 paramiko SOCKS5 动态隧道(编程式认证,解决 ssh -D 密码交互卡死):
   `python jump_socks.py <jump_ip> <port> <user> <pass> <local_port>` — 深圳 → `127.0.0.1:20800`(OKPay 已用此端口)
2. 请求走 `socks5h://127.0.0.1:20800`(requests 支持;勿用 urllib+socks 打 HTTPS 会 SSL EOF)
3. 验证出口:国内跳板访问 api.ipify.org 不通属**正常**(被墙),直接以目标可达/业务响应为准

## Pitfalls
- 4 台为国内电信 IP,访问境外目标走国际出口;若目标挡大陆 IP 需另找海外出口
- 新出口 IP 干净时保持低频,防二次风控(触发"已记录取证"会再次拉黑新 IP)
- 隧道脚本 jump_socks.py 若丢失:paramiko 起 local SOCKS5(no-auth + CONNECT)转发 direct-tcpip channel,~60 行可重写;技能正文有方法
