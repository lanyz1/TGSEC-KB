#!/usr/bin/env python3
"""
sxp — Sanitized eXPort：agent 家当「净化导出 + 敌对验证」一条流水线
=================================================================
把技能库/人格/记忆打成可迁移副本，并且**证明**它干净、能用、没打坏。

  sxp build  [opts]        构建净化包（净化 → 残留自检 → 语法门禁 → 打包）
  sxp verify <包|目录>      敌对验证（对**包本体**跑，不信构建现场）
  sxp all    [opts]        build + verify，任一步失败即非零退出
  sxp restore <包> [opts]  还原到目标 HERMES_HOME

设计铁律（每条都是用事故换的，详见 skill: agent-backup-restore）：
  · 打码必须 fail-closed：残留自检/语法门禁不过 → 直接 exit 1，不出货
  · 验证必须针对**交付件**：解包再扫，不验构建暂存目录
  · 正则分隔符一律 [ \\t]，绝不用 \\s（\\s 吃换行 → 把下一行标识符当值打掉）
  · 采集主机名用 re.ASCII（\\b 是 Unicode 感知的，中文贴域名会漏采）
  · 边界守卫不能把 '.' 算进左边界（会挡掉 *.x.com / ${y}.x.com）
  · 云厂商域不列白名单（目标自有 bucket 挂在 digitalocean/amazonaws/aliyuncs 上）
  · py_compile 会生成 __pycache__ → 先门禁、再清、最后打包
  · 技能库是移动靶 → 构建前后比 mtime 指纹
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tarfile, tempfile, time
from collections import Counter
from pathlib import Path

VERSION = "1.0.0"
PH = "[{}-REDACTED]"          # 占位符模板
PLACEHOLDER_RE = re.compile(r'\[(?:SECRET|PASS|API-KEY|TG-TOKEN|JWT|KEY|NODE-CRED|UUID|EMAIL|PHONE|WALLET|HEX|TARGET-HOST|TARGET-IP)-REDACTED\]')

# ───────────────────────── 默认配置 ─────────────────────────
DEF = dict(
    src        = "~/.hermes/skills",
    soul       = "~/.hermes/SOUL.md",
    memories   = "~/.hermes/memories",
    config     = "~/.hermes/config.yaml",
    env        = "~/.hermes/.env",
    out        = "~/hermes-exports",
    # 陈旧重复快照(会与新技能同名 → 目标机加载歧义), 一律排除
    exclude_dirs  = ["*.bak.*", "*.bak", "__pycache__", ".curator_backups", ".git"],
    exclude_files = [".curator_ledger.jsonl", ".bundled_manifest", ".usage.json",
                     ".curator_state", ".usage.json.lock", "MEMORY.md.lock", "USER.md.lock",
                     ".DS_Store", ".env", "SOUL.md", "USER.md", "MEMORY.md"],
    exclude_ext   = [".pyc", ".pyo"],
    # 实战/战役笔记目录（活体目标身份的采集源）
    live_dirs     = ["security/pentest-execution",
                     "security/fofa-mapping-unauth-services"],
    # 额外真值字面量（源码里挖出的硬编码口令/密钥，逐个精确替换）
    extra_literals = [],
)

# 已公开的通用哈希 —— 放行，不算泄露
PUBLIC_HASH = {"e10adc3949ba59abbe56e057f20f883e","21232f297a57a5a743894a0e4a801fc3",
    "5f4dcc3b5aa765d61d8327deb882cf99","25d55ad283aa400af464c76d713c07ad",
    "0192023a7bbd73250516f069df18b500","c33367701511b4f6020ec61ded352059",
    "4297f44b<PHONE-REDACTED>b2497399d7a93","d8578edf8458ce06fbc5bb76a58c5ca4",
    "e99a18c428cb38d5f260853678922e03","5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8",
    "7c222fb2927d828af22f592134e8932480637c0d","8cb2237d0679ca88db6464eac60da96345513964",
    "d41d8cd98f00b204e9800998ecf8427e","0d107d09f5bbe40cade3de5c71e9e9b7"}
# 官方示例值 —— 不算泄露
FP_VALUES = {"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}

# 知名公共/厂商/示例域 —— 采黑名单时放行
BENIGN_RE = re.compile(
    r'(github|gitlab|google|gstatic|microsoft|apple|cloudflare|nginx\.org|apache\.org|'
    r'oracle|python\.org|pypi|npmjs|example\.|domain\.com|target\.com|localhost|test\.|'
    r'163\.com|qq\.com|docker|redis\.io|elastic|jenkins|grafana|atlassian|mozilla|'
    r'kernel\.org|debian|ubuntu|shodan|censys|virustotal|abuseipdb|ipinfo|ip-api|maxmind|'
    r'ripe\.net|wikipedia|stackoverflow|medium|openai|anthropic|deepseek|w3\.org|json\.org|'
    r'ietf|rfc-editor|cve\.org|nist|mitre|kali|metasploit|exploit-db|vulhub|hacktricks|'
    r'portswigger|owasp|php\.net|golang|rust-lang|nodejs|jetbrains|vmware|cisco|'
    r'apachefriends|xampp|laragon|telegram\.org|t\.me|reddit|twitter|huggingface|vercel|'
    r'netlify|heroku|ngrok|trycloudflare|interactsh|oast\.|dnslog|ceye|requestbin|'
    r'webhook\.site|ifconfig\.me|ip-api\.com|ipinfo\.io|line\.me|wa\.me|whatsapp\.com|'
    r'zalo\.me|bing|yahoo|linkedin|facebook|instagram|youtube|bilibili|weibo|zhihu|baidu|'
    r'feishu|larksuite|notion|n8n\.io|airtable|zapier|openssl|zlib|sqlite|postgresql|'
    r'mysql\.com|mariadb|mongodb|slack|discord|discourse|gitea|forgejo|qemu|ffmpeg|videolan|'
    r'7-zip|win-rar|notepad-plus|ghidra|radare|traefik|jfrog|citrix|netscaler|mikrotik|'
    r'dlink|totolink|tenda|tp-link|honeywell|sonicwall|fortinet|ivanti|paltoalto|'
    r'[FOFA-MIRROR-REDACTED]|fofa|nosec|chinaz|googleapis|gstatic|w3\.org)', re.I)
# 注: digitalocean/amazonaws/s3/aliyuncs/oss 故意不在上面 —— 目标自有 bucket 挂其上
BENIGN_HOSTS = {"t.com","x.com","a.com","b.com","foo.com","bar.com","abc.com","yourdomain.com",
                "your-domain.com","myhost.com","mydomain.com","test-host.com","[FOFA-MIRROR-REDACTED]",
                "fofa.info","api.fofa.info","i.nosec.org","nsec.org","crt.sh","bit.ly",
                "tinyurl.com","is.gd","myip.ipip.net","ip.sb","cip.cc","checkip.amazonaws.com",
                "nip.io","sslip.io","xip.io","localtest.me"}
# 文件名样式 —— 不是主机，绝不进黑名单（否则 wp-login.php / crt.sh 会打坏代码）
FILE_LIKE_RE = re.compile(r'\.(sh|py|js|mjs|ts|md|json|txt|php|html?|yml|yaml|conf|ini|sql|db|'
                          r'log|csv|xml|bak|zip|tar|gz|xz|7z|png|jpe?g|svg|lock|toml|cfg|env|'
                          r'key|pem|crt|cer|service|dll|exe|bin|1)$', re.I)

HOST_RE = re.compile(
    r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|cc|top|xyz|net|org|vip|club|io|info|'
    r'site|online|app|fun|live|biz|pro|shop|store|link|one|icu|wang|asia|tv|fm|gg|to|be|me|us|'
    r'co|cn|jp|kr|sg|hk|tw|vn|id|ru|de|fr|uk|nl|br|pl|se|no|fi|es|pt|gr|cz|tr|il|ae|za|ke|pk|'
    r'bd|lk|np|my|th|ph|ws|bz|gd|vc|am|la|ly|sh|it|mn|pw|su|st|ml|ga|cf|gq|tk)\b', re.I | re.ASCII)
IP_RE = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', re.ASCII)
BENIGN_IP = {"127.0.0.1","0.0.0.0","8.8.8.8","1.1.1.1","127.0.0.2","127.0.0.3",
             "10.0.0.1","192.168.1.1","192.168.0.1","255.255.255.0","255.255.255.255",
             "169.254.169.254","169.254.169.123","100.100.100.200","100.96.0.96",
             "1.2.3.4","192.0.2.1","203.0.113.1","198.51.100.1","224.0.0.1","239.255.255.250"}

RULES = [
    ("AI/云 API key", re.compile(r'\b(sk-[A-Za-z0-9_\-]{16,}|xai-[A-Za-z0-9]{16,}|'
        r'AIza[0-9A-Za-z_\-]{30,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|'
        r'AKIA[0-9A-Z]{16}|hf_[A-Za-z0-9]{20,}|BQ[A-Za-z0-9_\-]{30,}|'
        r'glpat-[A-Za-z0-9_\-]{15,}|xox[baprs]-[A-Za-z0-9\-]{10,})'), PH.format("API-KEY")),
    ("Telegram bot token", re.compile(r'\b\d{8,12}:AA[A-Za-z0-9_\-]{30,}\b'), PH.format("TG-TOKEN")),
    ("JWT", re.compile(r'\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{5,}'), PH.format("JWT")),
    ("key=长值", re.compile(r'(?i)\bkey=([A-Za-z0-9]{24,64})\b'), "key="+PH.format("KEY")),
    ("节点凭据", re.compile(r'(?i)\b(public_?key|short_?id|pbk)[ \t]*[:=][ \t]*["\']?([A-Za-z0-9_\-]{10,60})["\']?'),
        r'\1='+PH.format("NODE-CRED")),
    ("UUID", re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'), PH.format("UUID")),
    ("邮箱", re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'), PH.format("EMAIL")),
    ("手机号", re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)'), PH.format("PHONE")),
    ("TRC20/BTC钱包", re.compile(r'\b(T[A-Za-z0-9]{33}|bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b'),
        PH.format("WALLET")),
    ("ETH钱包", re.compile(r'\b0x[a-fA-F0-9]{40}\b'), PH.format("WALLET")),
]
# 口令: 强标签可跟裸值; 值后必须词边界且不能是函数名/属性
PW_RE = re.compile(
    r'(?i)\b(password|passwd|paypassword|pwd|passphrase|pass|secret_?key|secret|api_?key|'
    r'apikey|密码|口令)\b([ \t]*[:=]{1,2}[ \t]*)(["\'`(\[]?)'
    r'([A-Za-z0-9!@#$%^&*._\-+/]{3,64})(["\'`)\]]?)(?![A-Za-z0-9_.])(?![ \t]*\()(?![ \t]*\[)')
# key/token 只在值被引号包着时才打 —— 否则 key=lambda x: 会被打坏
# 值字符集**不含 + ( )** —— 否则 `"key="+PH.format("KEY")` 这种代码表达式会被误判成口令赋值
PW_KEY_RE = re.compile(r'(?i)\b(key|token)\b([ \t]*[:=]{1,2}[ \t]*)(["\'])([A-Za-z0-9!@#$%^&*._\-]{3,64})\3(?![ \t]*\()')
PW_KEEP = {"str","password","admin","admin123","admin888","123456","1234","root","test","pass","1",
           "changeme","user_password","certpass","cert_pass","userpassword","artifactory","username",
           "gen","none","null","secret","example","demo","***","\"\"","''","yourpass","newpassword",
           "oldpassword","admin@123","p@ssw0rd","passw0rd"}
PW_KEEP_RE = re.compile(r'^(\{|<|\$|\[|\*|\(|\\|@|USER_|MY_|YOUR_|PASS_|TEST_|ADMIN_)')


def expand(p: str) -> Path:
    return Path(os.path.expanduser(p)).resolve()


# ═══════════════════════ 采集 ═══════════════════════
class Ctx:
    def __init__(self, cfg):
        self.cfg = cfg
        self.literals: set[str] = set(FP_VALUES)
        self.live_hosts: set[str] = set()
        self.live_ips: set[str] = set()
        self.stats = Counter()
        self._hb: dict[str, re.Pattern] = {}
        self._ib: dict[str, re.Pattern] = {}
        self.HOSTS_ALL: re.Pattern | None = None
        self.IPS_ALL: re.Pattern | None = None

    def harvest_literals(self):
        env = expand(self.cfg["env"])
        if env.exists():
            for line in env.read_text(errors="ignore").splitlines():
                m = re.match(r'^([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|PASS)[A-Z0-9_]*)'
                             r'\s*=\s*(.+)$', line)
                if m:
                    v = m.group(2).strip().strip('"').strip("'")
                    if len(v) >= 16 and not v.startswith("$"):
                        self.literals.add(v)
        for v in self.cfg.get("extra_literals", []):
            if v:
                self.literals.add(v)
        return self

    def harvest_hosts(self):
        roots = [expand(self.cfg["src"]) / d for d in self.cfg["live_dirs"]]
        mem = expand(self.cfg["memories"])
        if mem.exists():
            roots.append(mem)
        for base in roots:
            if not base.exists():
                continue
            for f in base.rglob("*"):
                if not f.is_file():
                    continue
                try:
                    t = f.read_text(errors="ignore")
                except Exception:
                    continue
                for h in HOST_RE.findall(t):
                    hl = h.lower().rstrip(".")
                    if BENIGN_RE.search(hl) or FILE_LIKE_RE.search(hl) or hl in BENIGN_HOSTS:
                        continue
                    self.live_hosts.add(hl)
                for ip in IP_RE.findall(t):
                    if ip not in BENIGN_IP and not ip.startswith(("192.168.","10.","172.1","172.2","172.3","127.")):
                        self.live_ips.add(ip)
        self.build_combined()
        return self

    def build_combined(self):
        """把主机/IP黑名单编成**单个交替正则**（长串优先=最长匹配）。
        逐条 subn 对 800+ 文件 × 250+ 主机 = 20 万次正则编译，这是唯一的性能瓶颈。"""
        def mk(items, pre, post):
            if not items:
                return None
            order = sorted(items, key=len, reverse=True)
            return re.compile(pre + '(?:' + '|'.join(re.escape(x) for x in order) + ')' + post, re.I)
        self.HOSTS_ALL = mk(self.live_hosts, r'(?<![A-Za-z0-9_\-])(?<![A-Za-z0-9_\-]\.)', r'(?![A-Za-z0-9_\-])')
        self.IPS_ALL   = mk(self.live_ips,   r'(?<![\d.])', r'(?![\d.])')
        return self

    def present(self, texts) -> tuple[set, set]:
        """返回仍出现在文本里的黑名单主机/IP（任何命中即泄露）"""
        hs, ips = set(), set()
        for t in texts:
            if self.HOSTS_ALL:
                hs |= {m.group(0).lower() for m in self.HOSTS_ALL.finditer(t)}
            if self.IPS_ALL:
                ips |= {m.group(0) for m in self.IPS_ALL.finditer(t)}
        return hs, ips

    # 精确替换: 边界守卫 —— 只挡「更长主机名的一部分」, 不挡 *.x.com / ${y}.x.com
    def host_bound(self, h):   # 缓存: 逐条编译是 O(文件×主机)
        rx = self._hb.get(h)
        if rx is None:
            rx = re.compile(r'(?<![A-Za-z0-9_\-])(?<![A-Za-z0-9_\-]\.)' + re.escape(h) +
                            r'(?![A-Za-z0-9_\-])', re.I)
            self._hb[h] = rx
        return rx

    def ip_bound(self, ip):
        rx = self._ib.get(ip)
        if rx is None:
            rx = re.compile(r'(?<![\d.])' + re.escape(ip) + r'(?![\d.])')
            self._ib[ip] = rx
        return rx

    def sanitize(self, text: str) -> str:
        st = self.stats
        for lit in self.literals:
            if lit and lit in text:
                st["字面量密钥"] += text.count(lit)
                text = text.replace(lit, PH.format("SECRET"))
        for name, rx, rep in RULES:
            text, n = rx.subn(rep, text)
            if n: st[name] += n
        if self.HOSTS_ALL:
            text, n = self.HOSTS_ALL.subn(PH.format("TARGET-HOST"), text)
            if n: st["活体域名"] += n
        if self.IPS_ALL:
            text, n = self.IPS_ALL.subn(PH.format("TARGET-IP"), text)
            if n: st["活体IP"] += n
        def _pw(m):
            v = m.group(4)
            if v.lower() in PW_KEEP or PW_KEEP_RE.match(v):
                return m.group(0)
            st["口令值"] += 1
            return f"{m.group(1)}{m.group(2)}{m.group(3)}{PH.format('PASS')}{m.group(5)}"
        text = PW_RE.sub(_pw, text)
        text, n = PW_KEY_RE.subn(
            lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{PH.format('PASS')}{m.group(3)}", text)
        if n: st["口令值(key/token带引号)"] += n
        def _hex(m):
            if m.group(0).lower() in PUBLIC_HASH:
                return m.group(0)
            st["长hex密钥"] += 1
            return PH.format("HEX")
        text = re.sub(r'\b[a-fA-F0-9]{32,64}\b', _hex, text)
        text, n = re.subn(r'\b[a-fA-F0-9]{8,31}(?=…|\.\.\.)', PH.format("HEX"), text)
        if n: st["截断hex密钥"] += n
        return text


# ═══════════════════════ build ═══════════════════════
CODE_EXT = {".py",".js",".mjs",".cjs",".ts",".sh",".bash",".zsh",".json",".yaml",".yml",
            ".php",".go",".rb",".java",".xml",".toml",".ini",".conf",".cfg",".sql",".env",".htaccess"}

def adjacency_check(files, label=""):
    """打码邻接自检: 代码文件里占位符零间距紧跟方括号或圆括号 → 打断代码表达式。
    只在代码文件里查: markdown 里占位符后面跟中文说明属于正常行文, 不算损坏。"""
    bad = []
    for f in files:
        if f.suffix.lower() not in CODE_EXT:
            continue
        try: t = f.read_text(errors="ignore")
        except Exception: continue
        for m in re.finditer(r'\[[A-Z\-]+-REDACTED\](?=[\[(])', t):
            bad.append(f"{f}:{t[:m.start()].count(chr(10)) + 1}")
    return bad

def snapshot(root: Path, exclude_dirs) -> str:
    acc = hashlib.sha256()
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not _excluded_dir(d, exclude_dirs)]
        for fn in sorted(files):
            p = Path(r) / fn
            try:
                acc.update(str(p).encode()); acc.update(str(p.stat().st_mtime_ns).encode())
            except Exception:
                pass
    return acc.hexdigest()


def _excluded_dir(name, pats):
    import fnmatch
    for p in pats:
        if any(c in p for c in "*?["):
            if fnmatch.fnmatch(name, p):
                return True
        elif name == p:
            return True
    return False


def do_build(cfg, name=None, keep_dir=True) -> Path:
    src = expand(cfg["src"])
    if not src.exists():
        sys.exit(f"❌ 源目录不存在: {src}")
    name = name or f"export-{time.strftime('%Y%m%d-%H%M')}"
    out = expand(cfg["out"]) / name
    if out.exists():
        shutil.rmtree(out)
    stage = out / "skills"
    stage.mkdir(parents=True)

    ctx = Ctx(cfg).harvest_literals().harvest_hosts()
    print(f"== 采集 ==\n  真值字面量 {len(ctx.literals)} / 活体域名 {len(ctx.live_hosts)} / 活体IP {len(ctx.live_ips)}")
    before = snapshot(src, cfg["exclude_dirs"])

    print("== 净化 ==")
    n = 0
    for r, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not _excluded_dir(d, cfg["exclude_dirs"])]
        for fn in files:
            p = Path(r) / fn
            if fn in cfg["exclude_files"] or p.suffix in cfg["exclude_ext"]:
                continue
            d = stage / p.relative_to(src)
            d.parent.mkdir(parents=True, exist_ok=True)
            raw = p.read_bytes()
            if b"\x00" in raw[:4096]:
                d.write_bytes(raw)
            else:
                try:
                    d.write_text(ctx.sanitize(raw.decode("utf-8", errors="ignore")), encoding="utf-8")
                except Exception:
                    d.write_bytes(raw)
            n += 1
    print(f"  技能文件 {n} 个")

    # 人格 / 记忆 / 配置
    soul = expand(cfg["soul"])
    if soul.exists():
        (out / "soul").mkdir(exist_ok=True)
        shutil.copy2(soul, out / "soul" / "SOUL.md")
        print("  神魂 SOUL.md ✓")
    mem = expand(cfg["memories"])
    if mem.exists():
        (out / "memories").mkdir(exist_ok=True)
        for m in ("MEMORY.md", "USER.md"):
            f = mem / m
            if f.exists():
                (out / "memories" / m).write_text(ctx.sanitize(f.read_text(errors="ignore")), encoding="utf-8")
        print("  记忆 ✓")
    (out / "config").mkdir(exist_ok=True)
    cfgf = expand(cfg["config"])
    if cfgf.exists():
        (out / "config" / "config.yaml").write_text(ctx.sanitize(cfgf.read_text()), encoding="utf-8")
    envf = expand(cfg["env"])
    if envf.exists():
        lines = []
        for line in envf.read_text(errors="ignore").splitlines():
            m = re.match(r'^([A-Z0-9_]+)=(.*)$', line)
            if m and re.search(r'KEY|TOKEN|SECRET|PASSWORD|PASS', m.group(1)) and m.group(2).strip():
                lines.append(f"{m.group(1)}=")
            else:
                lines.append(line)
        (out / "config" / "env.template").write_text(
            ctx.sanitize("\n".join(lines) + "\n"), encoding="utf-8")

    # ── fail-closed 1: 黑名单残留自检 ──
    resid = []
    for f in stage.rglob("*"):
        if not f.is_file():
            continue
        try:
            t = f.read_text(errors="ignore")
        except Exception:
            continue
        hs, ips = ctx.present([t])
        if hs or ips:
            resid.append((str(f.relative_to(stage)), (sorted(hs) + sorted(ips))[0]))
    if resid:
        print(f"  ❌ 黑名单残留 {len(resid)} 处 → 中止")
        for p, h in resid[:10]:
            print(f"     {p}: {h}")
        sys.exit(1)
    print(f"  ✅ 残留自检通过 ({len(ctx.live_hosts)} 主机 / {len(ctx.live_ips)} IP 全清)")

    # ── fail-closed 2: 语法门禁 ──
    print("== 语法门禁 ==")
    fails = []
    for f in stage.rglob("*"):
        if not f.is_file():
            continue
        s = f.suffix
        try:
            if s == ".py":
                compile(f.read_text(errors="ignore"), str(f), "exec")   # 进程内编译, 免 800 次 subprocess
            elif s == ".sh":
                r = subprocess.run(["bash", "-n", str(f)], capture_output=True)
                if r.returncode: fails.append((str(f.relative_to(stage)), r.stderr.decode()[:120]))
            elif s == ".json":
                json.loads(f.read_text(encoding="utf-8-sig", errors="ignore"))
            elif f.name == "SKILL.md":
                head = f.read_text(errors="ignore").split("\n")
                if not head[0].startswith("---") or not any(l.startswith("name:") for l in head[1:10]):
                    fails.append((str(f.relative_to(stage)), "frontmatter 坏"))
        except Exception as e:
            if s == ".json":
                fails.append((str(f.relative_to(stage)), f"json: {e}"))
    if fails:
        print(f"  ❌ 门禁未过 {len(fails)} 个 → 中止")
        for p, e in fails[:15]:
            print(f"     {p}: {e}")
        sys.exit(1)
    print("  ✅ 脚本可编译 / JSON 可解析 / frontmatter 完好")
    adj = adjacency_check([f for f in stage.rglob("*") if f.is_file()])
    if adj:
        print(f"  ❌ 打码邻接异常 {len(adj)} 处(占位符紧贴 [ 或 ( → 打断代码) → 中止")
        for x in adj[:10]: print(f"     {x}")
        sys.exit(1)
    print("  ✅ 打码邻接自检通过(无占位符打断代码结构)")
    for pc in list(stage.rglob("__pycache__")):
        shutil.rmtree(pc, ignore_errors=True)
    for pc in list(stage.rglob("*.pyc")):
        pc.unlink(missing_ok=True)

    # ── 移动靶守卫 ──
    if before != snapshot(src, cfg["exclude_dirs"]):
        print("  ⚠ 构建期间源目录被后台改写(curator) → 快照可能不一致, 建议重跑")
    else:
        print("  ✅ 源快照稳定")

    # 报告 + restore
    (out / "REDACTIONS.md").write_text(
        f"# 净化报告\n\n生成: {time.strftime('%Y-%m-%d %H:%M')}\n\n## 打码统计\n\n" +
        "\n".join(f"- {k}: {v}" for k, v in ctx.stats.most_common()) +
        f"\n\n黑名单: 活体域名 {len(ctx.live_hosts)} / IP {len(ctx.live_ips)}（精确边界匹配）\n"
        f"\n## 未打码\n- 通用默认口令（admin/admin123/123456 等公开知识）\n- 已公开的通用哈希\n"
        f"- 方法论、攻击链逻辑、脚本本体\n- 官方示例值\n", encoding="utf-8")
    (out / "RESTORE.sh").write_text(RESTORE_SH, encoding="utf-8")
    os.chmod(out / "RESTORE.sh", 0o755)

    tar = Path(str(out) + ".tar.gz")
    if tar.exists():
        tar.unlink()
    subprocess.run(["tar", "-czf", str(tar), "-C", str(out), "."], check=True)
    digest = hashlib.sha256(tar.read_bytes()).hexdigest()
    Path(str(tar) + ".sha256").write_text(f"{digest}  {tar.name}\n", encoding="utf-8")
    if not keep_dir:
        shutil.rmtree(out)
    print(f"\n== 产物 ==\n  {tar}\n  {tar.stat().st_size/1048576:.2f} MB  sha256={digest}")
    for k, v in ctx.stats.most_common():
        print(f"    {k}: {v}")
    return tar


# ═══════════════════════ verify ═══════════════════════
def do_verify(target: Path, cfg) -> int:
    """对**交付件**做敌对验证: 解包再扫。"""
    tmp = None
    if target.is_file():
        tmp = Path(tempfile.mkdtemp(prefix="sxp-verify-"))
        with tarfile.open(target) as t:
            t.extractall(tmp)
        root = tmp
    else:
        root = target
    skills = root / "skills" if (root / "skills").is_dir() else root
    fail, warn = [], []

    def ok(m): print(f"  ✅ {m}")
    def bad(m): print(f"  ❌ {m}"); fail.append(m)
    def wn(m): print(f"  ⚠  {m}"); warn.append(m)

    print("=" * 66); print("① 文件集 / 结构"); print("=" * 66)
    allf = [p for p in root.rglob("*") if p.is_file()]
    print(f"  文件 {len(allf)} / 技能 {len(list(skills.rglob('SKILL.md')))}")
    if (root / "soul" / "SOUL.md").exists(): ok("神魂在包内")
    else: wn("无 soul/SOUL.md（若本次不导人格可忽略）")
    if (root / "memories").is_dir(): ok("记忆在包内")
    if any(p.name.endswith(".pyc") for p in allf): bad("包内含 .pyc")
    else: ok("无 .pyc 污染")
    if any("REDACTED-HOSTS-LOCAL" in p.name for p in allf): bad("私密主机表被打进包")
    else: ok("私密主机表未进包")

    print("=" * 66); print("② 技能可加载性"); print("=" * 66)
    names, fm_bad, mism = Counter(), [], []
    for f in skills.rglob("SKILL.md"):
        lines = f.read_text(errors="ignore").split("\n")
        if not lines[0].startswith("---"): fm_bad.append(str(f)); continue
        m = re.search(r'^name:\s*["\']?([a-zA-Z0-9_\-]+)["\']?\s*$', "\n".join(lines[1:40]), re.M)
        if not m: fm_bad.append(str(f)); continue
        names[m.group(1)] += 1
        if m.group(1) != f.parent.name: mism.append((m.group(1), f.parent.name))
    dups = [n for n, c in names.items() if c > 1]
    if fm_bad: bad(f"frontmatter 不可解析 {len(fm_bad)}")
    else: ok(f"{len(names)} 个技能 frontmatter 可解析")
    if dups: bad(f"技能名冲突(目标机加载歧义): {dups}")
    else: ok("技能名全局唯一")
    if mism: wn(f"{len(mism)} 个 name 与目录名不一致: {mism[:3]}")
    else: ok("name 与目录名一致")

    print("=" * 66); print("③ 语法门禁（对包本体）"); print("=" * 66)
    bad_f, np_, ns, nj = [], 0, 0, 0
    for f in root.rglob("*"):
        if not f.is_file(): continue
        if f.suffix == ".py":
            np_ += 1
            try: compile(f.read_text(errors="ignore"), str(f), "exec")
            except Exception: bad_f.append(str(f.relative_to(root)))
        elif f.suffix == ".sh":
            ns += 1
            if subprocess.run(["bash", "-n", str(f)], capture_output=True).returncode:
                bad_f.append(str(f.relative_to(root)))
        elif f.suffix == ".json":
            nj += 1
            try: json.loads(f.read_text(encoding="utf-8-sig", errors="ignore"))
            except Exception: bad_f.append(str(f.relative_to(root)))
    if bad_f: bad(f"语法错误 {len(bad_f)}: {bad_f[:5]}")
    else: ok(f"py {np_} / sh {ns} / json {nj} 全部通过")
    for pc in list(root.rglob("__pycache__")):
        shutil.rmtree(pc, ignore_errors=True)
    for pc in list(root.rglob("*.pyc")):
        pc.unlink(missing_ok=True)

    print("=" * 66); print("④ 凭据 / PII 敌对扫描"); print("=" * 66)
    SCAN = {
        "OpenAI/云 sk-": r'\bsk-[A-Za-z0-9_\-]{16,}',
        "xai-": r'\bxai-[A-Za-z0-9]{16,}',
        "AIza": r'\bAIza[0-9A-Za-z_\-]{30,}',
        "ghp/gho/ghs": r'\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{20,}',
        "github_pat": r'\bgithub_pat_[A-Za-z0-9_]{20,}',
        "glpat": r'\bglpat-[A-Za-z0-9_\-]{15,}',
        "AWS AKIA": r'\bAKIA[0-9A-Z]{16}\b',
        "AWS secret": r'(?i)aws.{0,20}(?:secret|key)\s*[:=]\s*["\']?[A-Za-z0-9/+=]{30,}',
        "HF hf_": r'\bhf_[A-Za-z0-9]{20,}',
        "Slack xox": r'\bxox[baprs]-[A-Za-z0-9\-]{10,}',
        "TG bot token": r'\b\d{8,12}:AA[A-Za-z0-9_\-]{30,}\b',
        "JWT": r'\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{5,}',
        "私钥块": r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=\r\n]{60,}',
        "SSH key": r'ssh-(?:rsa|ed25519) AAAA[A-Za-z0-9+/]{40,}',
        "Bearer": r'(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{20,}',
        "带密码连接串": r'(?:mysql|postgres|redis|mongodb|amqp)://[^\s:]+:[^\s@]{4,}@',
        "key=长值": r'(?i)\bkey=[A-Za-z0-9]{24,}',
        "明文口令": r'(?i)\b(?:pass(?:word|wd)?|pwd|secret|token)\s*[:=]\s*["\']?[A-Za-z0-9!@#$%^&*._\-]{8,}["\']?\s*(?:$|[,;\)\]\}])',
        "手机号": r'(?<!\d)1[3-9]\d{9}(?!\d)',
        "邮箱": r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
        "TRC20/BTC": r'\b(T[A-Za-z0-9]{33}|bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b',
        "ETH": r'\b0x[a-fA-F0-9]{40}\b',
        "长hex": r'\b[a-fA-F0-9]{32,64}\b',
    }
    hits = Counter(); samples = {}
    for f in root.rglob("*"):
        if not f.is_file(): continue
        try: t = f.read_text(encoding="utf-8", errors="ignore")
        except Exception: continue
        for label, rx in SCAN.items():
            for m in re.finditer(rx, t):
                v = m.group(0)
                if "REDACTED" in v or v.strip() in FP_VALUES: continue
                if label == "长hex" and v.lower() in PUBLIC_HASH: continue
                if label == "明文口令":
                    val = re.sub(r'(?i)^\s*(pass(word|wd)?|pwd|secret|token)\s*[:=]\s*["\']?', '', v).rstrip('"\' )]};,')
                    if val.lower() in PW_KEEP or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', val) and \
                       (val.isupper() or (val[0].islower() and any(c.isupper() for c in val[1:]))):
                        continue
                hits[label] += 1
                samples.setdefault(label, []).append((str(f.relative_to(root)), v[:60]))
    adj = adjacency_check([f for f in root.rglob("*") if f.is_file()])
    if adj: bad(f"打码邻接异常 {len(adj)} 处(占位符紧贴 [ 或 ( ): {adj[:5]}")
    else: ok("打码邻接正常(无占位符打断代码)")

    if hits:
        for label, c in hits.items():
            bad(f"{label}: {c} 处 → {samples[label][:2]}")
    else:
        ok(f"{len(SCAN)} 类凭据/PII 规则 0 命中")

    print("=" * 66); print("⑤ 活体目标身份"); print("=" * 66)
    ctx = Ctx(cfg).harvest_literals().harvest_hosts()
    texts = []
    for f in root.rglob("*"):
        if f.is_file():
            try: texts.append(f.read_text(encoding="utf-8", errors="ignore"))
            except Exception: pass
    _sh, _si = ctx.present(texts)
    still, still_ip = sorted(_sh), sorted(_si)
    print(f"  候选: 域名 {len(ctx.live_hosts)} / IP {len(ctx.live_ips)}")
    if still or still_ip: bad(f"未打码 域名 {still[:8]} IP {still_ip[:5]}")
    else: ok("候选活体目标 100% 已打码")
    leaked = []
    for lit in ctx.literals:
        if any(lit in t for t in texts): leaked.append(lit[:24] + "…")
    if leaked: bad(f"真值泄露 {len(leaked)}: {leaked[:5]}")
    else: ok(f"{len(ctx.literals)} 个真值全部未泄露")

    print("=" * 66)
    print(f"结论: 失败 {len(fail)} / 警告 {len(warn)}")
    print("=" * 66)
    for f_ in fail: print("  ❌", f_)
    for w in warn: print("  ⚠ ", w)
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if fail else 0


# ═══════════════════════ restore ═══════════════════════
RESTORE_SH = r'''#!/usr/bin/env bash
# 还原净化包到 ~/.hermes/  (幂等: 已有内容先备份)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${HERMES_HOME:-$HOME/.hermes}"
STAMP="$(date +%Y%m%d%H%M%S)"
mkdir -p "$DEST"
warn(){ echo "  ⚠ $*"; }; ok(){ echo "  ✅ $*"; }

if [ -d "$HERE/skills" ]; then
  [ -d "$DEST/skills" ] && { cp -a "$DEST/skills" "$DEST/skills.bak.$STAMP"; ok "旧技能库已备份 → skills.bak.$STAMP"; }
  mkdir -p "$DEST/skills"
  cp -a "$HERE/skills/." "$DEST/skills/"
  ok "技能库 $(find "$HERE/skills" -name SKILL.md | wc -l) 个技能已还原"
fi
if [ -f "$HERE/soul/SOUL.md" ]; then
  [ -f "$DEST/SOUL.md" ] && cp -a "$DEST/SOUL.md" "$DEST/SOUL.md.bak.$STAMP"
  cp -a "$HERE/soul/SOUL.md" "$DEST/SOUL.md" && ok "神魂 SOUL.md 已装"
fi
if [ -d "$HERE/memories" ]; then
  mkdir -p "$DEST/memories"
  for m in MEMORY.md USER.md; do
    [ -f "$HERE/memories/$m" ] && cp -a "$HERE/memories/$m" "$DEST/memories/$m" && ok "记忆 $m 已装"
  done
fi
for f in config.yaml; do
  [ -f "$HERE/config/$f" ] || continue
  if [ -f "$DEST/$f" ]; then warn "$f 已存在未覆盖 → 参考件在 $HERE/config/$f"
  else cp -a "$HERE/config/$f" "$DEST/$f" && ok "$f 已装"; fi
done
if [ ! -f "$DEST/.env" ] && [ -f "$HERE/config/env.template" ]; then
  cp -a "$HERE/config/env.template" "$DEST/.env"
  warn ".env 由模板生成，密钥需手填: $(grep -oE '^[A-Z0-9_]*(KEY|TOKEN)[A-Z0-9_]*=' "$HERE/config/env.template" | tr -d '=' | paste -sd, -)"
fi
echo
echo "完成。重启 Hermes 生效（hermes gateway restart 或你的部署方式）"
'''


def do_restore(tar: Path, home: str):
    tmp = Path(tempfile.mkdtemp(prefix="sxp-restore-"))
    with tarfile.open(tar) as t:
        t.extractall(tmp)
    subprocess.run(["bash", str(tmp / "RESTORE.sh")], env={**os.environ, "HERMES_HOME": home}, check=True)
    shutil.rmtree(tmp, ignore_errors=True)


# ═══════════════════════ CLI ═══════════════════════
def load_cfg(path):
    cfg = dict(DEF)
    if path:
        cfg.update(json.loads(Path(path).read_text()))
    return cfg


def main():
    ap = argparse.ArgumentParser(prog="sxp", description="净化导出 + 敌对验证 一条流水线")
    ap.add_argument("--config", help="JSON 配置(覆盖默认)")
    ap.add_argument("--src"); ap.add_argument("--out"); ap.add_argument("--soul")
    ap.add_argument("--memories"); ap.add_argument("--config-file"); ap.add_argument("--env-file")
    ap.add_argument("--live-dir", action="append", default=[])
    ap.add_argument("--extra-literal", action="append", default=[])
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="构建净化包"); b.add_argument("--name"); b.add_argument("--no-dir", action="store_true")
    v = sub.add_parser("verify", help="敌对验证(对包本体)"); v.add_argument("target")
    a = sub.add_parser("all", help="build + verify"); a.add_argument("--name"); a.add_argument("--no-dir", action="store_true")
    r = sub.add_parser("restore", help="还原到 HERMES_HOME"); r.add_argument("target"); r.add_argument("--home", default=str(Path.home()/".hermes"))
    ap.add_argument("--version", action="version", version=f"sxp {VERSION}")
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    for key, val in (("src", args.src), ("out", args.out), ("soul", args.soul),
                     ("memories", args.memories), ("config", args.config_file), ("env", args.env_file)):
        if val:
            cfg[key] = val
    if args.live_dir:
        cfg["live_dirs"] = args.live_dir
    if args.extra_literal:
        cfg["extra_literals"] = DEF["extra_literals"] + args.extra_literal

    if args.cmd == "build":
        do_build(cfg, args.name, keep_dir=not args.no_dir)
    elif args.cmd == "verify":
        sys.exit(do_verify(Path(args.target).resolve(), cfg))
    elif args.cmd == "all":
        tar = do_build(cfg, args.name, keep_dir=not args.no_dir)
        print()
        rc = do_verify(tar, cfg)
        if rc:
            print("\n❌ 验证未通过 —— 包已生成但**不要**交付")
        else:
            print("\n✅ 构建 + 验证全过，可交付")
        sys.exit(rc)
    elif args.cmd == "restore":
        do_restore(Path(args.target).resolve(), args.home)


if __name__ == "__main__":
    main()
