#!/usr/bin/env python3
"""Telegram public-channel monitor + local session inventory (no API key)."""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.request
from pathlib import Path

CASES = Path("/root/cases")
POST = re.compile(r'data-post="([^"]+)".*?tgme_widget_message_text[^>]*>(.*?)</div>', re.S)


def accounts() -> list[str]:
    roots = [Path.home() / ".hermes", Path("/root"), Path("/root/tg_accounts"), Path("/root/sessions")]
    found = set()
    for root in roots:
        if root.exists():
            found |= {str(p) for p in root.rglob("*.session") if p.is_file()}
    return sorted(found)


def fetch(channel: str, timeout: float = 12) -> str:
    url = "https://t.me/s/" + channel.lstrip("@")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def parse(text: str) -> list[dict]:
    out = []
    for post, body in POST.findall(text):
        clean = re.sub(r"<[^>]+>", " ", body)
        out.append({"post": post, "text": html.unescape(re.sub(r"\s+", " ", clean)).strip()[:1000]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="TG 公开频道监控")
    ap.add_argument("action", choices=["list-accounts", "doctor", "run"], nargs="?", default="list-accounts")
    ap.add_argument("--channel", "-c")
    ap.add_argument("--config")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--interval", type=int, default=0, help="seconds; 0 = once")
    ap.add_argument("--case")
    args = ap.parse_args()
    if args.action == "list-accounts":
        for p in accounts():
            print(p)
        print(f"total={len(accounts())}")
        return 0
    if args.action == "doctor":
        print("mode: public t.me/s (no login); private groups require Telethon session")
        print("sessions:", len(accounts()))
        return 0
    channels = [args.channel] if args.channel else []
    if args.config:
        cfg = json.loads(Path(args.config).read_text())
        channels = cfg.get("channels", channels)
    if not channels:
        ap.error("--channel or --config required")
    result = {}
    while True:
        for ch in channels:
            try:
                posts = parse(fetch(ch))[-args.limit:]
                result[ch] = posts
                print(f"[{ch}] posts={len(posts)}")
                for p in posts[-3:]:
                    print(" ", p["post"], p["text"][:120])
            except Exception as e:
                print(f"[{ch}] ERROR {type(e).__name__}: {e}")
        if not args.interval:
            break
        time.sleep(max(10, args.interval))
    if args.case:
        case = Path(args.case) if Path(args.case).is_absolute() else CASES / args.case
        (case / "artifacts").mkdir(parents=True, exist_ok=True)
        out = case / "artifacts/tg_monitor.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[case]", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
