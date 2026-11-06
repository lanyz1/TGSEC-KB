# ServerStatus 2.0.0 (cppla Go rewrite)

## Public endpoints (no auth)
- `GET /api/health` → JSON with `agent.address`, `configPath` (e.g. `/app/config/config.json`), `service.version`, `service.generation`.
- `GET /json/stats.json` → public node stats. `servers[].custom` is the **output of the command the agent executed**, which proves config→command execution on the agent host.
- `GET /js/app.js` → panel JS; the admin token is read from `localStorage.serverstatusAdminToken`; API calls use `Authorization: Bearer <token>`.

## Admin API (token required)
- `GET /api/config` → full config (`servers`, `monitors`, `sslcerts`, `watchdog`).
- `POST /api/servers/{username}` → save one server object; the `custom` field is the command the agent runs.
- `POST /api/reload` → reload the config and push it to agents.
- Missing/wrong token: `401 {"error":"invalid or missing admin token"}`. On this build POST/PUT `/api/config` are 404/401; `/debug/pprof`, `/debug/vars`, and `/metrics` are 404.

## With a token (RCE path)
1. `GET /api/config`; copy a full server object (username, name, type, host, and all other fields).
2. Set `custom` to a probe: `id; uname -a; cat /proc/1/cgroup; ls -l /var/run/docker.sock`.
3. `POST /api/servers/<username>` with the full object, then `POST /api/reload`.
4. Poll `GET /json/stats.json`; read `servers[].custom` for the output.
5. The agent may be in a container as PID 1; check cgroup/mounts before assuming host root.
6. Cleanup: restore the original `custom` (usually empty) and reload.

## Without a token
- Try a file-read primitive for the `configPath`; the panel does not serve `/app/config/config.json` directly.
- Try secret reuse (old panel password, deploy secrets) once, then stop; do not brute a 32-hex token.
- The public `custom` output is evidence of the mechanism, not RCE by itself; the token is the gate. Do not report root from the public stats alone.
