## 十四、工具链

### 14.1 综合扫描
| 工具 | 用途 |
|------|------|
| fscan | 内网一体化扫描(存活/端口/弱口令/漏洞/Web) |
| LadonGo | 一键C/B/A段扫描+爆破+远程执行 |
| Netspy | 内网可达网段发现 |
| Yasso | 内网辅助工具集(含代理) |
| nmap/masscan | 端口与服务识别 |
| crackmapexec | 内网批量验证(协议矩阵) |

### 14.2 信息收集与凭证
| 工具 | 用途 |
|------|------|
| mimikatz | LSASS/ntds.dit/hash/票据 |
| SharpDecryptPwd | 常见软件密码批量解密 |
| HackBrowserData/SharpChromium | 浏览器凭据 |
| LaZagne | 多平台软件密码 |
| SharpCloud | 云凭证检查 |
| WinPEAS/PowerUp/les.sh | 提权自动枚举 |
| SharpHound/BloodHound | AD关系图与攻击路径 |

### 14.3 隧道与横向
| 工具 | 用途 |
|------|------|
| frp/Chisel/Neo-reGeorg/nps/pystinger | 隧道代理 |
| icmpsh/ptunnel/dnscat2/iodine | ICMP/DNS隧道 |
| impacket(psexec/wmiexec/smbexec/secretsdump) | 横向/凭证导出 |
| evil-winrm | WinRM横向 |
| Rubeus | Kerberos票据操作 |
| certipy | ADCS攻击 |
| noPac/zerologon/PrintSpoofer/GodPotato | 提权利用 |

### 14.4 AI/LLM相关
| 目标 | 检查工具/命令 |
|------|------|
| Ollama未授权 | `curl /api/tags` `/api/generate` |
| vLLM/推理网关 | `curl /v1/models` |
| 向量库未授权 | Milvus/Qdrant/Weaviate/Chroma API列表 |
| MCP服务器 | JSON-RPC `tools/list` |
| LLM平台后台 | Dify/FastGPT/Langflow弱口令 |

