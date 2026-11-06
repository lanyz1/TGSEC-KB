---
name: egress-rotation-and-ban-hygiene
description: "Use when a target bans source IPs; rotate egress safely."
version: 1.0.0
tags: [pentest, egress, vpn, tor, ban, rate-limit, proxy-rotation]
---

# Egress Rotation & Ban Hygiene

For targets that permanently ban source IPs (`40000 当前IP因异常访问已被永久封禁` and equivalents). Free-VPN/Tor/residential rotation is the only way to keep hitting an authenticated surface — and the failure mode this skill prevents is concluding **the endpoint is closed when only the exit was banned**.

## Always-on rules

1. **A negative is only valid from an egress the target still accepts.** A banned exit returns the ban code, an empty body, or a generic "resource not found" for *every* path. That is indistinguishable from "endpoint closed / needs auth". Never record a Deadend whose last test ran on an unverified exit.
2. **Budget the exit before you send.** Assume ~5–8 target requests per IP before a permanent ban — **but the budget is a function of the header set, not just the IP**: an API surface hit with a full browser header block sustained ~15–20 requests on one exit, where bare `curl` UA died on the first. Calibrate the budget on the surface you actually intend to hit, and never spend it on a request you have not given the full header set. Clean-check 1 + captcha 1 + register 1 + login 1 leaves **2–4 probes** on a captcha-gated flow. Rank the probes by value first; never spend the tail on low-value checks.
3. **Tokens are IP-bound.** A token issued on exit A returns `登录已失效` / `30000` on exit B. Register a fresh account per node and use it only there.
4. **Never retry a burned exit.** Keep an exit blacklist file and skip those IPs; free VPN pools recycle nodes, so a "fresh" IP can already sit on the target's permanent blacklist and return the ban code on its **first** request. **But a first-request ban is not proof of a pre-blacklisted IP — check the fingerprint before you file it as one.** A brand-new exit killed on its first bare-`curl` request, where an identically-placed exit with the full browser header block passed and stayed alive for many requests, was burned by its UA, not by its reputation. Before writing an exit to the blacklist as "already banned", re-send that same request once from another fresh exit **with the full header set**: it passes ⇒ the previous exit died to fingerprint (and the lesson is the header rule, not the blacklist); it dies the same way ⇒ then it really is reputation, and rotate on.
5. **Free failures first.** Registration failures usually do not ban the IP; a single wrong login does. Test the free failure mode (register / reset-options) before spending the costly one (login).
6. **An app-level ban is not a network ban — look for a CDN-fronted hostname before rotating.** When *every* exit gets `000`/TLS reset on a panel port (1Panel `:29433`, Directus, etc.) but the same service is also published under a Cloudflare-proxied hostname (`panel.<domain>`), the ban is keyed on your egress IPs and the CDN host sidesteps it — the peer the app sees is the CF edge, not you. Split the two states with one request each: `curl --interface <ip>` across all exits ⇒ all `000`; the same path via the CDN hostname ⇒ `200`. Costs zero rotation budget. Such bans are permanent — do not wait them out. It removes only the IP ban, **not** app-layer captcha or rate limits: re-check the login flow separately.
7. **Calibrate fail2ban before loading a dictionary; a global ban window masquerades as a tiny per-IP threshold.** Send ~20 sequential connections from one exit and record the exact attempt where the socket dies. If an earlier run already sent thousands and a *fresh* exit now dies at ~9, the target is inside a global/temporary ban window — not a per-IP limit of 9. Wait the window out and re-measure on a verified-clean exit before recording "brute force infeasible".
8. **`--interface <ip>` breaks name resolution — pair it with `--resolve`.** curl binds the source address and then resolves the hostname through that interface; when the bound address is a NAT/alias with no route to DNS, curl exits `6` (`Could not resolve host`) and nothing leaves the box — which reads exactly like a dead exit. Resolve once (`dig +short <host>`) and send `curl --interface <ip> --resolve <host>:<port>:<ipv4> https://<host>/`. That combination is the correct way to compare exits against one hostname; an exit-6 / `000` row is a client-side failure and must never be filed as "exit banned" or "target down".

## Per-node procedure

1. Bring the tunnel up and print the exit IP (`curl --interface tun0 https://api.ipify.org`).
2. Clean-check with ONE request — but pick the path by **which rules it traverses**, not by how cheap it is. A static site root or `/actuator/health` only proves the static layer is unblocked; WAF rules are grouped per path, so a node can answer `200 / 135B` on the root and still be banned on the business prefix you came for. Best value is to **merge the clean-check into the first real probe**: send your target prefix (empty or minimal body) with the full browser header set and read the business error code — `登录账号不能为空` / `401` / a validation message proves both "exit clean" and "route live" in one request, while the ban code kills the node at the same cost. Judge the **body**, never the HTTP status alone.
3. Run `scripts/check_exit_clean.sh <iface> <probe_url> [ban_pattern]` for a one-line verdict (`exit=… method=… len=… verdict=CLEAN|BANNED|SUSPECT_EMPTY|AUTH_WALL`). The script always sends the full browser header block — never hand-roll a bare `curl` probe, that is what burns exits. Set `METHOD=POST BODY='{}'` (plus `TOKEN`/`ORIGIN`/`REFERER` when you have them) to probe the real business prefix as your first move; `AUTH_WALL` means the exit is clean and the route reached the gateway.
4. Captcha-gated register: fetch captcha + key **through the same tunnel**, read the 4-char code with vision on the 5× upscale, register, login, then spend the remaining budget on the pre-planned probes. If the platform rejects the code (`130000`), fetch a **new** key — never resend a used key.
5. After the ban, rotate to a new node, append the dead exit to the blacklist, repeat.

## Hunter-script false positives

Empty bodies are tunnel artifacts, not findings. Before believing a `HIT`, print the body length and inspect with `cat -A`: a path line followed by nothing is a dropped connection. Grep-based hunters that flag any non-empty response will flag these on every run.

**A body only counts for the request that produced it.** On a transport failure curl exits non-zero and leaves the `-o` file holding the *previous* response, so a stale ban page gets read as a fresh ban against a clean exit — or against a host that never resolved at all. Gate every body read on `size_download > 0` (or use a per-probe temp file) before quoting a ban code, and never rotate an exit on a `000` row.

## Every sweep needs a control request

A vhost sweep, path sweep or ID sweep that comes back all-negative proves nothing unless one known-good request rode along **through the same interface in the same run**. Pair them deliberately:

- control also fails (`000`, curl exit 7, empty body) ⇒ transport/exit broke mid-run, the sweep never reached the target — rerun, do not record negatives.
- control returns the ban code ⇒ the exit burned mid-run; the later rows are invalid, rerun them on a new exit.
- control OK ⇒ the all-negative is real.

Read the failure mode before assigning a verdict: `000` is TLS/transport (often SNI rejected for a host that has no vhost), empty body with exit 0 is a dropped connection, and an application JSON code is a real answer. "Connection failed" must never be written up as "host not found".

## WAF path-prefix whitelist vs encoded URI

If the plain path returns the WAF/ban code but a percent-encoded variant reaches the application (a *different* error: validation message, `登录账号不能为空`, a `traceId`), the WAF matches the **raw URI string**, not the decoded route. One character suffices (`/platform/auth/%6Cogin` = `/platform/auth/login`). Keep the unencoded request as the control so "bypass worked" is never confused with "the IP is clean now".

## Reporting

State the egress state with each conclusion: `verified clean exit → tested → result`. Findings from unverified nodes are SUSPECTED, not VALIDATED; negatives from them are not dead ends.

## Scripts

- `scripts/check_exit_clean.sh` — one-line exit-IP + clean/banned verdict through a given interface.
