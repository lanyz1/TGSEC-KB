#!/usr/bin/env python3
"""Email security probe: parse .eml or a lure HTML page, no network.

Subcommands:
  eml  --path <mail.eml> [--case <case>] [--json]
  lure --path <page.html> [--case <case>] [--json]

The tool is read-only. With --case it writes a JSON artifact under
/root/cases/<case>/artifacts/ and never prints raw credentials.
"""
from __future__ import annotations

import argparse
import email
import hashlib
import json
import re
import sys
from email import policy
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.I)
URGENCY = ("urgent", "immediately", "verify your account", "suspend", "过期", "立即", "冻结", "验证")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_path(case: str, name: str) -> Path:
    base = Path("/root/cases") / case / "artifacts"
    base.mkdir(parents=True, exist_ok=True)
    return base / name


def emit(data: dict, as_json: bool, case: str | None, name: str) -> None:
    if case:
        path = artifact_path(case, name)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        data = {**data, "artifact": str(path)}
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print(f"mode={data['mode']} source={data['source']}")
    for key in ("from", "to", "subject", "message_id", "auth", "indicators"):
        if key in data:
            value = data[key]
            if isinstance(value, list):
                print(f"{key}: {len(value)}")
                for item in value[:20]:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")
    if data.get("urls"):
        print(f"urls: {len(data['urls'])}")
        for url in data["urls"][:30]:
            print(f"  - {url}")
    if data.get("attachments"):
        print(f"attachments: {len(data['attachments'])}")
        for item in data["attachments"]:
            print(f"  - {item['filename']} ({item['size']} bytes, {item['sha256'][:16]}…)")


def parse_eml(path: Path) -> dict:
    raw = path.read_bytes()
    msg = email.message_from_bytes(raw, policy=policy.default)
    headers = {k.lower(): str(v) for k, v in msg.items()}
    body_text = ""
    html_text = ""
    attachments = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        filename = part.get_filename()
        payload_raw = part.get_payload(decode=True)
        payload = payload_raw if isinstance(payload_raw, bytes) else b""
        if filename:
            attachments.append({
                "filename": filename,
                "content_type": ctype,
                "size": len(payload),
                "sha256": sha256_bytes(payload),
            })
        elif ctype == "text/plain":
            body_text += part.get_content()
        elif ctype == "text/html":
            html_text += part.get_content()

    combined = body_text + "\n" + html_text
    urls = []
    for url in URL_RE.findall(combined):
        if url not in urls:
            urls.append(url.rstrip(".,;)]"))
    from_addr = headers.get("from", "")
    reply_to = headers.get("reply-to", "")
    return_path = headers.get("return-path", "")
    auth = headers.get("authentication-results", "")
    from_host = parseaddr(from_addr)[1].split("@")[-1].lower() if "@" in parseaddr(from_addr)[1] else ""
    reply_host = parseaddr(reply_to)[1].split("@")[-1].lower() if "@" in parseaddr(reply_to)[1] else ""
    return_host = parseaddr(return_path)[1].split("@")[-1].lower() if "@" in parseaddr(return_path)[1] else ""
    indicators = []
    if from_host and reply_host and reply_host != from_host:
        indicators.append("reply-to differs from from-domain")
    if from_host and return_host and return_host != from_host:
        indicators.append("return-path differs from from-domain")
    text_l = combined.lower()
    for word in URGENCY:
        if word in text_l:
            indicators.append(f"urgency phrase: {word}")
    if re.search(r"display\s*:\s*none|font-size\s*:\s*0|visibility\s*:\s*hidden", html_text, re.I):
        indicators.append("hidden html content")
    if re.search(r"<form\b", html_text, re.I):
        indicators.append("html form in email")
    return {
        "mode": "eml",
        "source": str(path),
        "from": from_addr,
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "message_id": headers.get("message-id", ""),
        "reply_to": reply_to,
        "return_path": return_path,
        "auth": auth,
        "spf": "pass" if "spf=pass" in auth.lower() else ("fail" if "spf=fail" in auth.lower() else "unknown"),
        "dkim": "pass" if "dkim=pass" in auth.lower() else ("fail" if "dkim=fail" in auth.lower() else "unknown"),
        "dmarc": "pass" if "dmarc=pass" in auth.lower() else ("fail" if "dmarc=fail" in auth.lower() else "unknown"),
        "urls": urls,
        "attachments": attachments,
        "indicators": indicators,
    }


class LureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[dict] = []
        self.scripts: list[str] = []
        self.iframes: list[str] = []
        self.meta_refresh: list[str] = []
        self.inputs: list[dict] = []
        self._current_form: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "form":
            self._current_form = {"action": a.get("action", ""), "method": a.get("method", "get"), "inputs": []}
            self.forms.append(self._current_form)
        elif tag == "input":
            item = {"type": a.get("type", "text"), "name": a.get("name", ""), "autocomplete": a.get("autocomplete", "")}
            self.inputs.append(item)
            if self._current_form is not None:
                self._current_form["inputs"].append(item)
        elif tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        elif tag == "iframe" and a.get("src"):
            self.iframes.append(a["src"])
        elif tag == "meta" and a.get("http-equiv", "").lower() == "refresh":
            self.meta_refresh.append(a.get("content", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._current_form = None


def parse_lure(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    parser = LureParser()
    parser.feed(raw)
    indicators = []
    if any(i.get("type") == "password" for i in parser.inputs):
        indicators.append("password field")
    if parser.iframes:
        indicators.append("iframe present")
    if re.search(r"\beval\s*\(|\batob\s*\(|\bunescape\s*\(|fromCharCode", raw, re.I):
        indicators.append("obfuscated javascript")
    if re.search(r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0", raw, re.I):
        indicators.append("hidden content")
    domains = []
    for url in parser.scripts + parser.iframes + [f.get("action", "") for f in parser.forms]:
        host = urlparse(url).hostname
        if host and host not in domains:
            domains.append(host)
    return {
        "mode": "lure",
        "source": str(path),
        "forms": parser.forms,
        "inputs": parser.inputs,
        "scripts": parser.scripts,
        "iframes": parser.iframes,
        "meta_refresh": parser.meta_refresh,
        "external_domains": domains,
        "indicators": indicators,
        "sha256": sha256_bytes(path.read_bytes()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only email/lure artifact probe")
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("eml", "lure"):
        p = sub.add_parser(name)
        p.add_argument("--path", required=True)
        p.add_argument("--case")
        p.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path = Path(args.path).expanduser()
    if not path.is_file():
        print(f"email_sec_probe: file not found: {path}", file=sys.stderr)
        return 2
    try:
        data = parse_eml(path) if args.command == "eml" else parse_lure(path)
    except Exception as exc:
        print(f"email_sec_probe: parse failed: {exc}", file=sys.stderr)
        return 1
    emit(data, args.json, args.case, f"email_sec_probe_{args.command}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
