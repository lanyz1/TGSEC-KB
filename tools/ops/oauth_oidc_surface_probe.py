#!/usr/bin/env python3
"""OAuth2 / OIDC discovery and redirect_uri surface probe (read-only).

Usage:
  oauth_oidc_surface_probe.py --base https://target --scope target.example
  oauth_oidc_surface_probe.py --base https://target --scope target.example --client-id abc

Checks:
  - openid-configuration / oauth-authorization-server metadata
  - PKCE, implicit/password grants, token auth methods
  - authorization endpoint behavior with an unregistered redirect_uri
Never exchanges credentials and never follows redirects.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope_lint import host_of, load_scope, matches  # noqa: E402

TIMEOUT = 10
UA = "TGSEC-oauth-probe/1.0"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url: str, timeout: int = TIMEOUT) -> tuple[int, dict, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(2_000_000).decode("utf-8", "replace")
            return resp.status, dict(resp.headers), body
    except urllib.error.HTTPError as exc:
        body = exc.read(200_000).decode("utf-8", "replace")
        return exc.code, dict(exc.headers), body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, {}, str(exc)


def parse_json(body: str) -> dict:
    try:
        data = json.loads(body)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def discover(origin: str, timeout: int) -> tuple[str | None, dict, list[dict]]:
    errors: list[dict] = []
    for path in ("/.well-known/openid-configuration", "/.well-known/oauth-authorization-server"):
        url = origin.rstrip("/") + path
        status, headers, body = fetch(url, timeout)
        if status == 200:
            data = parse_json(body)
            if data:
                return url, data, errors
        errors.append({"url": url, "status": status, "content_type": headers.get("Content-Type", "")})
    return None, {}, errors


def probe_redirect(auth_endpoint: str, client_id: str, timeout: int) -> dict:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": "https://example.invalid/tgsec-callback",
        "scope": "openid",
        "state": "tgsec",
    }
    url = auth_endpoint + ("&" if "?" in auth_endpoint else "?") + urllib.parse.urlencode(params)
    status, headers, _ = fetch(url, timeout)
    location = headers.get("Location", "")
    host = urlparse(location).hostname if location else ""
    return {
        "request_url": url,
        "status": status,
        "location": location,
        "unregistered_redirect_accepted": bool(host == "example.invalid"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only OAuth2/OIDC surface probe")
    ap.add_argument("--base", required=True, help="authorized base URL")
    ap.add_argument("--scope", action="append", default=[], help="inline scope entry")
    ap.add_argument("--scope-file", help="scope file, one host per line")
    ap.add_argument("--client-id", default="tgsec-test-client")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--case")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    target = host_of(args.base)
    entries = load_scope(args.scope_file, args.scope)
    if not target or not entries or not any(matches(target, e)[0] for e in entries):
        print("[scope] DENY: explicit --scope/--scope-file matching the target is required", file=sys.stderr)
        return 2

    parsed = urlparse(args.base if "://" in args.base else "https://" + args.base)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    source, config, errors = discover(origin, args.timeout)
    result: dict = {
        "mode": "oauth_oidc",
        "base": origin,
        "scope_host": target,
        "discovery_url": source,
        "discovery_errors": errors,
        "config": config,
        "findings": [],
    }

    if config:
        methods = config.get("code_challenge_methods_supported") or []
        grants = config.get("grant_types_supported") or []
        token_methods = config.get("token_endpoint_auth_methods_supported") or []
        if not methods:
            result["findings"].append({"severity": "MED", "rule": "PKCE not advertised", "value": methods})
        if "implicit" in grants:
            result["findings"].append({"severity": "MED", "rule": "implicit grant enabled", "value": grants})
        if "password" in grants:
            result["findings"].append({"severity": "HIGH", "rule": "password grant enabled", "value": grants})
        if "none" in token_methods:
            result["findings"].append({"severity": "INFO", "rule": "public client token auth (none)", "value": token_methods})
        auth_ep = config.get("authorization_endpoint")
        if isinstance(auth_ep, str) and auth_ep:
            redirect = probe_redirect(auth_ep, args.client_id, args.timeout)
            result["redirect_test"] = redirect
            if redirect["unregistered_redirect_accepted"]:
                result["findings"].append({"severity": "HIGH", "rule": "unregistered redirect_uri accepted", "value": redirect["location"]})

    if args.case:
        out = Path("/root/cases") / args.case / "artifacts"
        out.mkdir(parents=True, exist_ok=True)
        target_file = out / "oauth_oidc_surface_probe.json"
        target_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result["artifact"] = str(target_file)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"base={origin} discovery={'ok' if config else 'none'} findings={len(result['findings'])}")
        for item in result["findings"]:
            print(f"[{item['severity']}] {item['rule']} -> {item['value']}")
        for error in errors:
            print(f"[discovery-miss] {error['url']} status={error['status']}")
    return 0 if config else 1


if __name__ == "__main__":
    raise SystemExit(main())
