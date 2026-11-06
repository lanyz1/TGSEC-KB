# Account-keyed lockout (Tor will not help)

## Signal
Responses like:
- `账号错误次数超过限制，请3分钟后重试`
- `账号或密码错误4!admin` / `错误N!…` counting down on the **same username**

While rotating Tor exits / random `--proxy-user` still hits the same lock → counter is **per account**, not per IP.

## Do
1. Stop high-rate spray immediately.
2. Cap **≤3 verify attempts per window** on that username.
3. Hard sleep **≥ stated cooldown** (often 180–210s); refresh player/admin token if needed.
4. Resume next window; keep durable state of tried passwords.
5. Optionally probe **alt usernames** (existence oracle) in separate slow windows — still account-keyed per name.

## Don't
- Burn Tor circuits hoping the lock clears.
- Parallel workers on the same username.
- Treat path/IP WAF bans the same as this (those belong to `waf-fronted-login-attack`).

## Case
712win3 `/adminapi/verify` via player forward: Tor slow spray still locked on `admin`; 3/window + 210s was the workable pace (no HIT in that session).
