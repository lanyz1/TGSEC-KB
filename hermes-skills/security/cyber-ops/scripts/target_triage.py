#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cyber-ops 目标分类辅助:关键词 → 匹配候选技能(从 profile security 技能库检索)。
用法:
  python target_triage.py "<目标描述/关键词>"          # 按关键词搜技能
  python target_triage.py --list-all                  # 列出全部技能名
  python target_triage.py --domain web|reverse|crack  # 按域预过滤
输出: 匹配技能名 + description 触发词(供 planner 决定加载哪些技能)
纯 stdlib,无网络依赖。
"""
import os, re, sys, glob

SECURITY_DIR = os.path.expanduser(r"tools/ops")
# 域 → 关键词黑名单(用于 --domain 预过滤)
DOMAIN_KEYWORDS = {
    "web":    ["pentest", "web", "api", "spa", "saas", "graphql", "sql", "faka", "casino", "bot", "shop", "jwt", "oauth", "csrf", "ssti", "xxe", "ssrf", "cloudflare", "edgeone", "thinkphp", "cms", "crawler", "websocket", "wasm", "lowcode", "smart-parking", "parking", "tg-", "callback", "captcha", "frontend-auth"],
    "reverse": ["reverse", "crack", "keygen", "patch", "disasm", "unpack", "anti-debug", "nuitka", "pyinstaller", "flutter", "dart", "apk", "ios", "ipa", "golang", "dotnet", "python-reverse", "tiandun", "fndata", "electron", "card-key", "windows-exe", "binary-protect", "codex-backend"],
    "crack":  ["crack", "keygen", "card-key", "license", "卡密", "注册机", "verification", "auth-server", "fake-auth", "callback-signature"],
}

def load_index():
    """遍历 security 技能目录,读每个 SKILL.md 的 frontmatter name/description。"""
    idx = []
    for md in sorted(glob.glob(os.path.join(SECURITY_DIR, "*", "SKILL.md"))):
        name = os.path.basename(os.path.dirname(md))
        desc = ""
        try:
            with open(md, encoding="utf-8", errors="replace") as f:
                head = f.read(3000)
            m = re.search(r"^description:\s*(.+)$", head, re.M)
            if m:
                desc = m.group(1).strip()[:300]
        except Exception:
            pass
        idx.append({"name": name, "desc": desc})
    return idx

def score(name, desc, kw):
    """轻量评分:关键词命中 name=3分, desc 命中=1分。"""
    s = 0
    k = kw.lower()
    if k in name.lower():
        s += 3
    if k in desc.lower():
        s += 1
    return s

def main():
    args = sys.argv[1:]
    idx = load_index()
    if "--list-all" in args:
        for e in idx:
            print(f"{e['name']:<45} {e['desc'][:70]}")
        print(f"TOTAL={len(idx)}")
        return
    domain = None
    if "--domain" in args:
        i = args.index("--domain")
        domain = args[i + 1] if i + 1 < len(args) else None
        args = args[:i] + args[i + 2:]
    query = " ".join(args).strip()
    if not query and not domain:
        print("用法: python target_triage.py \"关键词\" | --domain web|reverse|crack | --list-all")
        return
    kws = [w for w in re.split(r"[,\s/]+", query) if w] if query else []
    if domain:
        kws += DOMAIN_KEYWORDS.get(domain, [])
    scored = []
    for e in idx:
        s = sum(score(e["name"], e["desc"], kw) for kw in kws)
        if s > 0:
            scored.append((s, e))
    scored.sort(key=lambda x: -x[0])
    for s, e in scored[:25]:
        print(f"[{s:>2}] {e['name']:<45} {e['desc'][:80]}")
    print(f"MATCHED={len(scored)} of {len(idx)}")

if __name__ == "__main__":
    main()
