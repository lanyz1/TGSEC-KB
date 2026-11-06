#!/usr/bin/env python3
"""净化导出器 — 把技能/知识树打成"可分发副本"：剥掉密钥/PII/活体目标身份，保留方法与流程。

对照 skill: agent-backup-restore「净化导出模式」（规则表与坑见 references/sanitized-export.md）。

用法:
  python3 sanitize_export.py --src ~/.hermes/skills --out /tmp/exp \\
      --live-dir security/pentest-execution/references \

产出:
  <out>/skills/                     净化后的树
  <out>/REDACTIONS.md               打码统计（可随包分发，不含被打码的值）
  <out>/REDACTED-HOSTS-LOCAL.txt    被打码的主机/IP 全表（**不进包**）

务必按文档里的验证清单再跑一遍反向扫描——不验就等于没做。
"""
import argparse, os, re, shutil, datetime
from pathlib import Path
from collections import Counter

EXCLUDE_FILES = {"SOUL.md", "USER.md", "MEMORY.md",
                 ".curator_ledger.jsonl", ".bundled_manifest"}
EXCLUDE_DIRS  = {"__pycache__", ".curator_backups"}
EXCLUDE_EXT   = {".pyc", ".pyo"}
PLACEHOLDER   = "[%s-REDACTED]"

BENIGN_HOST_RE = re.compile(
    r'(github\.com|gitlab\.com|githubusercontent|google\.com|gstatic|microsoft\.com|apple\.com|'
    r'cloudflare\.com|nginx\.org|apache\.org|oracle\.com|python\.org|pypi\.org|npmjs|'
    r'example\.(com|org|net)|domain\.com|target\.com|localhost|test\.(com|local)|'
    r'aliyun|amazonaws\.com|163\.com|qq\.com|docker\.com|redis\.io|elastic\.co|jenkins\.io|'
    r'grafana\.com|atlassian|mozilla\.org|kernel\.org|debian\.org|ubuntu\.com|'
    r'shodan\.io|censys\.io|virustotal|abuseipdb|ipinfo\.io|ip-api|maxmind|ripe\.net|'
    r'wikipedia\.org|stackoverflow|w3\.org|json\.org|ietf\.org|rfc-editor|'
    r'cve\.org|nvd\.nist\.gov|mitre\.org|kali\.org|exploit-db|vulhub|hacktricks|portswigger|owasp\.org|'
    r'php\.net|golang\.org|rust-lang|nodejs\.org|jetbrains\.com|vmware\.com|cisco\.com|'
    r'telegram\.org|t\.me|interactsh|oast\.(live|me|pro|fun|site|online)|dnslog|ceye\.io|'
    r'webhook\.site|requestbin|w3\.org|mariadb|mysql\.com|mongodb|postgresql|sqlite\.org|'
    r'openssl\.org|qemu\.org|ffmpeg\.org|videolan|7-zip\.org|openssh|traefik\.io)', re.I)
HOST_RE = re.compile(r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+'
                     r'(?:com|cc|top|xyz|net|org|vip|club|io|info|site|online|app|fun|live|cn|me|'
                     r'us|biz|pro|shop|store|link|one|icu|wang|ren|asia|co|tv|fm|gg|to|sh|'
                     r'be|it|jp|kr|sg|hk|tw|ph|th|vn|id|my|in|ru|de|fr|uk|nl|br|mx|pl|se|no|'
                     r'fi|dk|es|pt|gr|cz|sk|hu|ro|bg|ua|tr|il|ae|sa|eg|za|ng|ke|pk|bd|lk|np)', re.I)
IP_RE = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
BENIGN_IP = {"127.0.0.1", "127.0.0.2", "0.0.0.0", "8.8.8.8", "1.1.1.1",
             "255.255.255.0", "255.255.255.255", "10.0.0.1", "192.168.1.1"}
SENSITIVE_NAME_HINT = re.compile(r'(casino|bet|togel|slot|gambl|poker|bocai|caipiao|lottery|kefu)', re.I)

RULES = [
    ("AI/云 API key", re.compile(r'\b(sk-[A-Za-z0-9_\-]{16,}|xai-[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_\-]{30,}|'
                                 r'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|'
                                 r'hf_[A-Za-z0-9]{20,}|BQ[0-9A-Za-z_\-]{30,}|glpat-[A-Za-z0-9_\-]{15,})\b'), "API-KEY"),
    ("Telegram bot token", re.compile(r'\b\d{8,12}:AA[A-Za-z0-9_\-]{30,}\b'), "TG-TOKEN"),
    ("JWT", re.compile(r'\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{5,}'), "JWT"),
    ("通用key=值", re.compile(r'(?i)\bkey=([A-Za-z0-9]{24,64})\b'), "KEY"),
    ("代理节点凭据", re.compile(r'(?i)(public_?key|short_?id|pbk|sid)[ \t]*[:=][ \t]*["\']?([A-Za-z0-9_\-]{8,60})["\']?'), "NODE-CRED"),
    ("UUID", re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'), "UUID"),
    ("邮箱", re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'), "EMAIL"),
    ("手机号", re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)'), "PHONE"),
    ("TRC20/BTC地址", re.compile(r'\b(T[A-Za-z0-9]{33}|bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b'), "WALLET"),
    ("ETH地址", re.compile(r'\b0x[a-fA-F0-9]{40}\b'), "WALLET"),
    ("长hex串", re.compile(r'\b[a-fA-F0-9]{32,64}\b'), "HEX"),
]
PW_RE = re.compile(
    r'(?i)\b(password|passwd|paypassword|pwd|passphrase|pass|密码|口令)\b([ \t]*[:=]{1,2}[ \t]*)'
    r'(["\'`(\[]?)([A-Za-z0-9!@#$%^&*._\-+/]{3,64})(["\'`)\]]?)')
PW_RE2 = re.compile(
    r'(?i)\b(password|passwd|paypassword|pwd|passphrase|密码|口令)[ \t]*[\(\[](?=[ \t`"\']|)'
    r'([A-Za-z0-9!@#$%^&*._\-+/]{5,64})[ \t`"\']*[\)\]]')
PW_KEEP = {"str", "password", "admin", "admin123", "admin888", "123456", "1234", "root",
           "test", "pass", "1", "changeme", "user_password", "certpass", "cert_pass",
           "userpassword", "artifactory", "username", "gen", "none", "null", "secret",
           "example", "demo", '""', "''"}
PLACEHOLDER_KEEP_RE = re.compile(r'^(\{|<|\$|\[|\*|\(|USER_|MY_|YOUR_|PASS_|TEST_|ADMIN_|\\|@)')


def collect_env_literals(env_path):
    lits = set()
    p = Path(env_path)
    if not p.exists():
        return lits
    for line in p.read_text(errors="ignore").splitlines():
        m = re.match(r'^([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|PASS)[A-Z0-9_]*)\s*=\s*(.+)$', line)
        if m:
            v = m.group(2).strip().strip('"').strip("'")
            if len(v) >= 16 and not v.startswith("$"):
                lits.add(v)
    return lits


def build_target_blacklist(src, live_dirs):
    hosts, ips = set(), set()
    for rel in live_dirs:
        base = Path(src) / rel
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if not f.is_file():
                continue
            try:
                txt = f.read_text(errors="ignore")
            except Exception:
                continue
            for h in HOST_RE.findall(txt):
                hl = h.rstrip(".").lower()
                if not BENIGN_HOST_RE.search(hl):
                    hosts.add(hl)
            for ip in IP_RE.findall(txt):
                if ip in BENIGN_IP or ip.startswith(("192.168.", "10.", "172.16.", "172.17.",
                                                     "172.18.", "127.")):
                    continue
                ips.add(ip)
    for h in list(hosts):
        if SENSITIVE_NAME_HINT.search(h):
            hosts.add(h)
    return hosts, ips


def make_sanitizer(literals, hosts, ips, stats):
    def sanitize(text):
        for lit in literals:
            if lit and lit in text:
                stats["字面量密钥"] += text.count(lit)
                text = text.replace(lit, PLACEHOLDER % "SECRET")
        for name, rx, tag in RULES:
            text, n = rx.subn(PLACEHOLDER % tag, text)
            if n:
                stats[name] += n

        def _pw(m):
            v = m.group(4)
            if v.lower() in PW_KEEP or PLACEHOLDER_KEEP_RE.match(v):
                return m.group(0)
            return "%s%s%s%s%s" % (m.group(1), m.group(2), m.group(3),
                                   PLACEHOLDER % "PASS", m.group(5))
        text, n = PW_RE.subn(_pw, text)
        if n:
            stats["口令值"] += n
        text, n = PW_RE2.subn(lambda m: "%s (%s)" % (m.group(1), PLACEHOLDER % "PASS"), text)
        if n:
            stats["口令值(括号式)"] += n
        # 截断显示的 hex 密钥 (17cf2f98…)
        text, n = re.subn(r'\b[a-fA-F0-9]{8,31}(?=…|\.\.\.)', PLACEHOLDER % "HEX", text)
        if n:
            stats["截断hex密钥"] += n
        # 【已移除】行内上下文规则（本行含 pass/key 等词 → 打码整行引号字面量）
        #   坑：命中面过宽，会把 passenger/openresty 这类普通单词打掉，
        #   且会把 `if password:` 换行后的标识符一起吃掉 → 源码语法坏。
        #   替代：只用上面带"标签+分隔符+值"的窄规则；分隔符一律 [ \t] 别用 \s（\s 吃换行）。

        text = HOST_RE.sub(
            lambda m: (stats.__setitem__("活体域名", stats["活体域名"] + 1) or
                       (PLACEHOLDER % "TARGET-HOST"))
            if m.group(0).rstrip(".").lower() in hosts else m.group(0), text)
        text = IP_RE.sub(
            lambda m: (stats.__setitem__("活体IP", stats["活体IP"] + 1) or
                       (PLACEHOLDER % "TARGET-IP"))
            if m.group(0) in ips else m.group(0), text)
        return text
    return sanitize


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--env", default=str(Path.home() / ".hermes/.env"))
    ap.add_argument("--live-dir", action="append", default=[],
                    help="实战 references 目录（相对 --src），用于提取活体目标黑名单")
    ap.add_argument("--exclude-dir", action="append", default=[],
                    help="整目录排除，如冗余快照目录")
    a = ap.parse_args()

    src, out = Path(a.src), Path(a.out)
    stage = out / "skills"
    ex_dirs = set(EXCLUDE_DIRS) | set(a.exclude_dir)

    literals = collect_env_literals(a.env)
    hosts, ips = build_target_blacklist(src, a.live_dir)
    stats = Counter()
    sanitize = make_sanitizer(literals, hosts, ips, stats)

    def excluded(p):
        if p.name in EXCLUDE_FILES or p.suffix in EXCLUDE_EXT:
            return True
        return any(part in ex_dirs for part in p.parts)

    if out.exists():
        shutil.rmtree(out)
    stage.mkdir(parents=True)
    n_files = n_skip = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in ex_dirs]
        for fn in files:
            p = Path(root) / fn
            if excluded(p):
                n_skip += 1
                continue
            dst = stage / p.relative_to(src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                raw = p.read_bytes()
            except Exception:
                n_skip += 1
                continue
            if b"\x00" in raw[:4096]:
                dst.write_bytes(raw)
            else:
                dst.write_text(sanitize(raw.decode("utf-8", errors="ignore")), encoding="utf-8")
            n_files += 1

    lines = ["# 净化导出报告\n", "生成: %s\n" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
             "文件: %d（跳过 %d）\n" % (n_files, n_skip), "## 排除项\n"]
    for f in sorted(EXCLUDE_FILES):
        lines.append("- %s" % f)
    for d in sorted(ex_dirs):
        lines.append("- %s/" % d)
    lines += ["", "## 打码统计\n"]
    for k, v in stats.most_common():
        lines.append("- %s: %d" % (k, v))
    (out / "REDACTIONS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "REDACTED-HOSTS-LOCAL.txt").write_text(
        "== 打码域名 ==\n" + "\n".join(sorted(hosts))
        + "\n\n== 打码IP ==\n" + "\n".join(sorted(ips)) + "\n", encoding="utf-8")

    print("STAGE=%s\n文件=%d 跳过=%d" % (stage, n_files, n_skip))
    for k, v in stats.most_common():
        print("  %s: %d" % (k, v))
    print("目标黑名单: 域名 %d / IP %d" % (len(hosts), len(ips)))
    print("注意: REDACTED-HOSTS-LOCAL.txt 不进包; 打完请按 references/sanitized-export.md 跑反向扫描")


if __name__ == "__main__":
    main()
