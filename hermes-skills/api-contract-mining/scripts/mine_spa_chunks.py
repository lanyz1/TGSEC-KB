#!/usr/bin/env python3
"""SPA chunk API miner (stdlib only).

usage:
    python3 mine_spa_chunks.py https://target/ /tmp/spa_out [--max 80]

1. 抓页面，找入口 bundle（/_nuxt/*.js、/assets/index-*.js）
2. BFS 展开 import("./x.js") 引用，下载全部 chunk
3. 对每个 chunk 正则抽 API 路径，写到 endpoints.txt

适配提示：正则按目标调整；有些站 chunk 名不带 .js 后缀（Nuxt3 的 _nuxt/XXXX 是裸 id），
那就把 CHUNK_RE 的 \\.js 去掉。
"""
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

ENTRY_RE = re.compile(r'src="([^"]+\.js[^"]*)"')
CHUNK_RE = re.compile(r'["\'](\.?/?[A-Za-z0-9_\-./]*?)\.js["\']')
PATH_RE = re.compile(r'["\'](/[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-{}$:]+){1,6})["\']')
VERB_RE = re.compile(r'\.(get|post|put|patch|delete)\s*\(\s*$', re.I)


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    base = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/spa_out"
    maxn = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 80
    os.makedirs(out, exist_ok=True)

    p = urllib.parse.urlparse(base)
    root = "%s://%s" % (p.scheme, p.netloc)
    html = get(base)

    queue = []
    for src in ENTRY_RE.findall(html):
        queue.append(urllib.parse.urljoin(base, src))
    if not queue:
        print("[!] 页面里没找到 entry bundle，手工看一眼 HTML")
        return 2

    seen, files = set(), {}
    while queue and len(seen) < maxn:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            body = get(url)
        except Exception as e:
            print("[!] %s -> %s" % (url, e))
            continue
        name = url.rsplit("/", 1)[-1].split("?")[0] or "index"
        files[name] = body
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(body)
        for ref in CHUNK_RE.findall(body):
            ref = ref.strip()
            if ref.endswith(".js"):
                ref = ref[:-3]
            cand = urllib.parse.urljoin(url, ref + ".js")
            if cand.startswith(root) and cand not in seen:
                queue.append(cand)
        print("[+] %-40s %7d B" % (name, len(body)))

    hits = set()
    for name, body in files.items():
        for m in PATH_RE.finditer(body):
            path = m.group(1)
            if not any(k in path for k in ("/",)):
                continue
            ctx = body[max(0, m.start() - 160):m.start()]
            verb = "ANY"
            vm = VERB_RE.search(ctx)
            if vm:
                verb = vm.group(1).upper()
            elif "method" in ctx.lower():
                verb = "POST?"
            hits.add((verb, path, name))

    with open(os.path.join(out, "endpoints.txt"), "w", encoding="utf-8") as f:
        for verb, path, src in sorted(hits, key=lambda x: (x[1], x[0])):
            f.write("%s %-52s %s\n" % (verb, path, src))

    print("\n[=] %d chunk, %d 候选路径 -> %s/endpoints.txt" %
          (len(files), len(hits), out))
    print("[=] 重点看 /upload /bind /status /admin /wallet /internal 这类路径")
    return 0


if __name__ == "__main__":
    sys.exit(main())
