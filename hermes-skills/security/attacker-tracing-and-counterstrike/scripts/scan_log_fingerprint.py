#!/usr/bin/env python3
"""access.log 攻击者指纹识别 —— 溯源第一步（只读，不改目标、不外连）。

用法:
  python3 scan_log_fingerprint.py --log access.log
  python3 scan_log_fingerprint.py --log /var/log/nginx/access.log --top 20 --json out.json
  tail -n 50000 /var/log/nginx/access.log | python3 scan_log_fingerprint.py --stdin

支持: nginx/apache combined、(common) 无 referer/ua 行；JSON lines（含 ip/request/user_agent 字段时自动识别）。
输出: 按源 IP 聚合（请求数 / 404 率 / 命中指纹 / 高危路径），终端表 + 可选 JSON。
判据强度见 references/attacker-fingerprint-dict.md；单独 UA 不足以定案。
"""
import argparse, json, re, sys
from collections import Counter, defaultdict

FP = [
    {"name": "AWVS/Acunetix", "strength": "强", "why": "工具专用请求头",
     "hdr": r"acunetix-(product|aspect|scanning-agreement)", "ua": None, "uri": None},
    {"name": "sqlmap", "strength": "强", "why": "默认 UA 带 sqlmap",
     "ua": r"sqlmap", "hdr": None, "uri": None},
    {"name": "CobaltStrike beacon", "strength": "中", "why": "默认 profile 的 C2 URI",
     "ua": None, "hdr": None, "uri": r"/(activity|submit\.php|pixel|updates|visit\.php)(\?|$)"},
    {"name": "AntSword", "strength": "中", "why": "UA 含 antSword",
     "ua": r"antsword", "hdr": None, "uri": None},
    {"name": "nuclei", "strength": "中", "why": "UA 含 nuclei",
     "ua": r"nuclei", "hdr": None, "uri": None},
    {"name": "xray/afrog", "strength": "中", "why": "UA 含工具名",
     "ua": r"(xray|afrog)", "hdr": None, "uri": None},
    {"name": "目录扫描器", "strength": "中", "why": "UA 含工具名",
     "ua": r"(dirsearch|feroxbuster|wfuzz|gobuster|ffuf|dirb)", "hdr": None, "uri": None},
    {"name": "Goby", "strength": "弱", "why": "UA 含 Goby（可改）",
     "ua": r"goby", "hdr": None, "uri": None},
    {"name": "菜刀/Chopper", "strength": "弱", "why": "旧 IE UA",
     "ua": r"msie [67]\.0", "hdr": None, "uri": None},
    {"name": "冰蝎/哥斯拉(疑)", "strength": "弱", "why": "固定 Chrome 83/84 段",
     "ua": r"chrome/8[34]\.", "hdr": None, "uri": None},
]

HIGH_RISK = [r"/\.git/", r"/\.svn/", r"/\.env", r"/\.DS_Store", r"\.zip$", r"\.sql$", r"\.bak$",
             r"/phpmyadmin", r"/pma/", r"/manager/html", r"/actuator", r"/druid/", r"/console/login",
             r"/owa/auth", r"/eval-stdin\.php", r"/vendor/phpunit", r"/wp-json/", r"/backup",
             r"/shell", r"/webshell", r"/admin", r"/login", r"/upload"]

LOG_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<method>[A-Z]+) (?P<uri>\S+)[^"]*" '
    r'(?P<status>\d{3}) (?P<size>\d+|-)')
UA_RE = re.compile(r'"\s(?P<ua>[^"]*)"\s*$')


def parse_line(line):
    line = line.rstrip("\n")
    if not line or line.startswith("#"):
        return None
    if line.lstrip().startswith("{"):
        try:
            o = json.loads(line)
        except ValueError:
            return None
        return {
            "ip": o.get("remote_addr") or o.get("ip") or o.get("client_ip") or "-",
            "uri": o.get("request") or o.get("uri") or o.get("url") or "-",
            "status": str(o.get("status") or o.get("status_code") or "-"),
            "ua": (o.get("http_user_agent") or o.get("user_agent") or o.get("ua") or ""),
            "raw": line,
        }
    m = LOG_RE.match(line)
    if not m:
        return None
    d = m.groupdict()
    ua = ""
    tail = line[m.end():]
    mu = re.search(r'"([^"]*)"\s*$', line)
    if mu:
        ua = mu.group(1)
    d["ua"] = ua
    d["raw"] = line
    return d


def hit(d):
    names, risk = [], []
    for f in FP:
        if f["ua"] and re.search(f["ua"], d["ua"], re.I):
            names.append(f["name"] + f"({f['strength']})")
        if f["uri"] and re.search(f["uri"], d["uri"], re.I):
            names.append(f["name"] + f"({f['strength']})")
        # 默认日志格式不含请求头；若日志格式里带 header 原文（$http_* / njs），hdr 规则仍可命中
        if f.get("hdr") and re.search(f["hdr"], d["raw"], re.I):
            names.append(f["name"] + f"({f['strength']})")
    names = list(dict.fromkeys(names))
    for p in HIGH_RISK:
        if re.search(p, d["uri"], re.I):
            risk.append(p.strip("/\\").replace("\\", "") or p)
    return names, risk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    if a.stdin or not a.log:
        fh = sys.stdin
    else:
        fh = open(a.log, "r", encoding="utf-8", errors="ignore")

    agg = defaultdict(lambda: {"n": 0, "404": 0, "ua": Counter(), "fp": Counter(), "risk": Counter(),
                               "uri": Counter()})
    total = 0
    for line in fh:
        d = parse_line(line)
        if not d:
            continue
        total += 1
        s = agg[d["ip"]]
        s["n"] += 1
        if d["status"].startswith("4"):
            s["404"] += 1
        if d["ua"]:
            s["ua"][d["ua"][:80]] += 1
        names, risk = hit(d)
        for nm in names:
            s["fp"][nm] += 1
        for r in risk:
            s["risk"][r] += 1
        s["uri"][d["uri"][:120]] += 1

    rows = []
    for ip, s in agg.items():
        score = len(s["fp"]) * 3 + min(len(s["risk"]), 10) + (2 if s["n"] > 200 else 0)
        rows.append({
            "ip": ip, "requests": s["n"], "err4xx": s["404"],
            "err_ratio": round(s["404"] / s["n"], 2) if s["n"] else 0,
            "fingerprints": dict(s["fp"]), "risk_paths": dict(s["risk"]),
            "top_ua": s["ua"].most_common(1)[0][0] if s["ua"] else "",
            "score": score,
        })
    rows.sort(key=lambda r: (-r["score"], -r["requests"]))

    print(f"# 解析行数: {total}  源 IP 数: {len(rows)}  (只读分析)")
    print(f"{'IP':<40}{'req':>7}{'4xx%':>7}  {'指纹':<28}高危路径")
    for r in rows[: a.top]:
        fpn = ",".join(r["fingerprints"]) or "-"
        rp = ",".join(list(r["risk_paths"])[:4]) or "-"
        print(f"{r['ip']:<40}{r['requests']:>7}{r['err_ratio']:>7}  {fpn:<28}{rp}")
    print("\n# 提示：UA 为弱特征，命中指纹后仍需 2 条证据 + 排除自有漏扫/拨测 IP 才定级。")
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump({"total_lines": total, "ips": rows}, f, ensure_ascii=False, indent=2)
        print(f"# JSON: {a.json_out}")


if __name__ == "__main__":
    main()
