"""
HTTP 探测脚本 — 通用 WAF 探测 + 端点测试
用法: python http_probe.py <target_url>
"""
import sys, requests, json, re
from urllib.parse import urljoin

def probe(target):
    target = target.rstrip('/')
    results = {"target": target, "tests": []}
    
    def test(name, url, method="GET", data=None, headers=None):
        h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        if headers:
            h.update(headers)
        try:
            if method == "POST":
                r = requests.post(url, data=data or {}, headers=h, timeout=10)
            else:
                r = requests.get(url, headers=h, timeout=10)
            entry = {
                "name": name, "status": r.status_code, "size": len(r.content),
                "waf_blocked": r.status_code == 406,
                "response_snippet": r.text[:120]
            }
            results["tests"].append(entry)
            icon = "⛔" if entry["waf_blocked"] else "✅"
            print(f"  {icon} {name}: HTTP {r.status_code} ({entry['size']} bytes)")
            return r
        except Exception as e:
            print(f"  ❌ {name}: {str(e)[:50]}")
            return None
    
    print(f"\n=== 基础探测: {target} ===\n")
    
    r = test("正常请求", target)
    
    # WAF 逐词测试
    waf_payloads = [
        ("单引号", "/?q='"),
        ("SELECT", "/?q=SELECT"),
        ("union+select", "/?q=union+select"),
        ("OR+1=1", "/?q=' OR 1=1"),
        ("script标签", "/?q=<script>"),
        ("路径穿越", "/?q=../etc/passwd"),
        ("information_schema", "/?q=information_schema"),
    ]
    for name, path in waf_payloads:
        test(f"WAF: {name}", target + path)
    
    # 常见端点
    common_paths = [
        "/admin", "/login", "/api", "/backup", "/.git/config",
        "/.env", "/phpinfo.php", "/robots.txt", "/sitemap.xml"
    ]
    for path in common_paths:
        test(f"路径: {path}", target + path)
    
    # Cookie 审计
    if r and r.cookies:
        print(f"\n=== Cookie 审计 ===")
        for cookie in r.cookies:
            issues = []
            if not cookie.secure: issues.append("无Secure")
            if 'httponly' not in str(cookie).lower(): issues.append("无HttpOnly")
            status = "⚠️ " + ", ".join(issues) if issues else "✅ 安全"
            print(f"  {cookie.name}: {status}")
    
    # 安全头部审计
    if r:
        security_headers = {
            "X-Frame-Options": "点击劫持",
            "X-XSS-Protection": "XSS保护",
            "X-Content-Type-Options": "MIME嗅探",
            "Content-Security-Policy": "CSP",
            "Strict-Transport-Security": "HSTS",
        }
        print(f"\n=== 安全头部 ===")
        for hdr, desc in security_headers.items():
            if hdr in r.headers:
                print(f"  ✅ {hdr} ({desc})")
            else:
                print(f"  ❌ 缺少 {hdr} ({desc})")
    
    out = f"probe_{target.replace('https://','').replace('http://','').replace('/','_')}.json"
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 已保存: {out}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python http_probe.py <target_url>")
        sys.exit(1)
    probe(sys.argv[1])
