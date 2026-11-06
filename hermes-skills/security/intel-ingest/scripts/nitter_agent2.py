#!/usr/bin/env python3
"""nitter fetcher with Anubis PoW solving + rate-limit retry. (intel-ingest toolkit)
Usage: nitter_agent2.py <handle> <pages> [instance-host]
OUT dir: env NITTER_OUT (default ./nitter_out)
"""
import subprocess, json, re, hashlib, sys, time, os

DEFAULT_INST = "nitter.meowing.monster"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
OUT = os.environ.get("NITTER_OUT", "./nitter_out")
os.makedirs(OUT, exist_ok=True)


def curl(url, jar, follow=True):
    cmd = ["curl", "-s", "-A", UA, "-b", jar, "-c", jar, "-m", "40"]
    if follow:
        cmd.insert(1, "-L")
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout


def solve_pow(data, difficulty):
    """Anubis 'fast' algo: sha256(data+nonce) hex; first difficulty/2 BYTES zero; odd difficulty -> high nibble zero."""
    p, odd, n = difficulty // 2, difficulty % 2, 0
    while True:
        h = hashlib.sha256((data + str(n)).encode()).digest()
        ok = all(h[i] == 0 for i in range(p))
        if ok and odd and (h[p] >> 4) != 0:
            ok = False
        if ok:
            return h.hex(), n
        n += 1


def get_page(url, jar, inst, tries=6):
    body = ""
    for t in range(tries):
        body = curl(url, jar)
        if "anubis_challenge" in body:
            m = re.search(r'<script id="anubis_challenge" type="application/json">(.*?)</script>', body, re.S)
            if not m:
                time.sleep(3)
                continue
            ch = json.loads(m.group(1))
            cid = ch["challenge"]["id"]
            data = ch["challenge"]["randomData"]
            diff = ch["rules"]["difficulty"]
            t0 = time.time()
            resp, nonce = solve_pow(data, diff)
            el = int((time.time() - t0) * 1000) + 2500
            redir = url.replace("https://" + inst, "") or "/"
            pass_url = (f"https://{inst}/.within.website/x/cmd/anubis/api/pass-challenge"
                        f"?id={cid}&response={resp}&nonce={nonce}&redir={redir}&elapsedTime={el}")
            out = curl(pass_url, jar)
            if "anubis_challenge" not in out and len(out) > 5000:
                return out
            time.sleep(2)
            continue
        low = body.lower()
        if "rate limited" in low or "no items found" in low or "try again" in low[:2000]:
            wait = 40 + t * 20
            print(f"  ..rate limited/no items, sleep {wait}s (try {t+1})")
            time.sleep(wait)
            continue
        # timeline not actually loaded (rate-limited shell page) -> retry
        if body.count('timeline-item') < 2 and t < tries - 1:
            wait = 45 + t * 20
            print(f"  ..timeline missing ({len(body)}B), sleep {wait}s (try {t+1})")
            time.sleep(wait)
            continue
        return body
    return body


def parse_tweets(html):
    tweets = []
    for it in re.split(r'<div class="timeline-item', html)[1:]:
        tl = re.search(r'<a class="tweet-link" href="([^"]+)"', it)
        dt = re.search(r'<span class="tweet-date"><a href="[^"]*" title="([^"]*)"', it)
        tc = re.search(r'<div class="tweet-content media-body"[^>]*>(.*?)</div>', it, re.S)
        if not tc:
            continue
        text = re.sub(r'<br\s*/?>', '\n', tc.group(1))
        text = re.sub(r'<[^>]+>', '', text).strip()
        link = tl.group(1) if tl else ''
        date = dt.group(1) if dt else ''
        if text or link:
            tweets.append((date, link, text))
    return tweets


def main():
    handle = sys.argv[1]
    npages = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    inst = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_INST
    base = f"https://{inst}"
    jar = f"{OUT}/.jar_{handle}_{inst.replace('.', '_')}"
    all_tweets = []
    url = f"{base}/{handle}"
    for page in range(npages):
        html = get_page(url, jar, inst)
        open(f"{OUT}/{handle}@{inst}_p{page+1}.html", "w").write(html)
        tw = parse_tweets(html)
        print(f"[{handle}@{inst}] p{page+1}: {len(html)}B, {len(tw)} tweets")
        all_tweets.extend(tw)
        cm = re.search(r'<div class="show-more"><a href="([^"]+)"', html)
        if not cm:
            print("  no show-more -> end")
            break
        url = f"{base}/{handle}{cm.group(1).replace('&amp;', '&')}"
        time.sleep(4)
    lines = [f"### {d}\nhttps://x.com{l}\n{t}\n" for d, l, t in all_tweets]
    open(f"{OUT}/{handle}_tweets.txt", "w").write("\n".join(lines))
    print(f"[{handle}] TOTAL {len(all_tweets)} tweets -> {handle}_tweets.txt")


if __name__ == "__main__":
    main()
