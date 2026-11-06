<!-- archived from /root/.hermes/skills/security/local-dev-server-ops/SKILL.md on 2026-10-21 -->

---
name: local-dev-server-ops
description: >-
  测绘引擎·Use when opening or checking a local web project/dev server.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/local-dev-server-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/local-dev-server-ops/…')`，不要相对 `references/legacy/` 解析。

# local-dev-server-ops（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/local-dev-server-ops/`

溯源（仅标记）：`hermes/software-development`

---

# Local Web Dev Server Ops (Windows + v2rayN box)

Recurring task class: user says 「打开本地XX项目」/「启动XX」/「查看XX项目进度」. This machine runs MANY projects (Qavlixor, TikFlow, BC sites, CTF tools) — always locate first, never assume.

## Workflow

1. **Locate the project** — don't trust names alone:
   - `search_files(target='files')` on `C:\Users\Administrator\Desktop` AND `D:\` with likely names (中文拼音/英文/品牌名都试).
   - Desktop folder is usually the ACTIVE copy; `D:\Codex\*` is often a STALE duplicate — confirm via git log dates / file mtimes (e.g. D:\Codex\touliu 6/29 vs Desktop\touliu 7/31).
   - Folder names can mislead: `D:\Codex\tiktok` actually holds Qavlixor code. Peek inside before trusting a name.
   - Project requirement/ops docs may live in a separate folder (e.g. Desktop\出海\ for TikFlow: touliu.txt=需求, tk账号.txt, tk一些网站.txt).

2. **Check progress** (when asked 项目进度):
   - `git log --oneline -20` + `git status -s` in the project dir — status shows uncommitted work.
   - Read README.md / DEPLOY.md / `.claude/forge/artifacts/*.md` for milestone batches (W1-W15 style) and 待办/安全 items.

3. **Check port occupancy BEFORE starting**:
   - `netstat -ano | grep LISTENING | grep -E ":3000|:3001"` — on this box **3000 is usually taken by Qavlixor's dev server**.
   - `.claude/devport.txt` / devserver.log can be STALE — trust netstat + curl, not those files.
   - **LISTENING ≠ responding**: a hung node dev server (multi-GB RAM) can hold the port while serving nothing — `curl` times out on it. Verify before blaming the proxy.

4. **Start on a free port** — NEVER kill another project's dev server without explicit user consent (铁律 #5; e.g. Qavlixor on 3000):
   - `cd <project> && PORT=3001 npx next dev -p 3001` via terminal(background=true, notify_on_complete=true).
   - Wait for `Ready in` / `Compiled` in the log before verifying.

5. **Verify**:
   - `curl -s -o /dev/null -w "HTTP %{http_code}" --noproxy '*' --max-time 10 http://127.0.0.1:PORT/` — use `--noproxy '*'` to bypass env/system proxy (v2rayN) for local checks.
   - Then browser_navigate to `http://localhost:PORT/<locale>`; check snapshot + browser_vision for render quality.
   - Smoke-test login with a seed account from README (e.g. demo@…/demo12345).

6. **Production / remote server checks**:
   - TCP connect success ≠ HTTP works: `curl -s -v --noproxy '*' http://IP/` — exit 52 / empty reply with port open ⇒ nginx/pm2 down, not network.
   - Local DNS/代理 fake-ip is untrustworthy for domain checks (W15 文档已确认) — verify DNS server-side (`dig @8.8.8.8 domain`) or curl `--resolve` to bypass local fake DNS.

## Pitfalls
- Stale log files (devport.txt, devserver.log) lie — verify live state with netstat + curl.
- Hung node processes hold ports while unresponsive; check RAM in tasklist (`tasklist /FI "PID eq N"`) — 4GB+ node = likely hung dev server.
- Never touch other projects' processes — use a different port instead.
- Report production outages with evidence (ports open / HTTP empty / DNS fake-ip), and flag security 待办 found in docs (e.g. plaintext root password in deploy notes).

## References
- `references/tikflow-project.md` — TikFlow (tk投流) project map: active/stale paths, stack, seed accounts, prod server, 2026-08 status.
