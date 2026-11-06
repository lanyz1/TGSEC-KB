---
name: hermes-model-provider-config
description: "Add custom model gateways so /model switching works."
version: 1.0.0
metadata:
  hermes:
    tags: [hermes, config, model, provider, aliases, gateway, custom]
---

# Hermes Custom Model Provider / Alias Config

Class-level skill for wiring custom OpenAI-compatible endpoints (zuz8.xyz,
ai.kugua.shop, bigmodel, moonshot, etc.) into Hermes so `/model <name>`
switching picks the right base_url AND api_key per model. Reused whenever the
user hands over a gateway URL + API key(s) and wants model switching.

## Where aliases live (CRITICAL gotcha)

Hermes reads TWO different alias stores, and they are NOT interchangeable:

- **Top-level `model_aliases:` (dict format) — the real one.**
  `_load_direct_aliases()` in `hermes_cli/model_switch.py` parses this as
dicts: `{model, provider, base_url, api_key}`. It honours per-alias
`base_url` + `api_key`. **Use THIS for anything with its own endpoint/key**
(zuz8, glm, sol, terra).

- **`model.aliases:` (SET VIA `hermes config set model.aliases.foo`) — string-only.**
  The same parser reads `model.aliases` but does `if not isinstance(value,
str): continue` — a dict entry is silently DROPPED. `hermes config set
model.aliases.foo '{...dict...}'` therefore does nothing except bloat config.
  Only `"provider/model"` string form works here.

**Rule: to add a custom gateway model, edit top-level `model_aliases:` — do NOT
use `hermes config set model.aliases.*` with a dict.**

## Correct entry shape

```yaml
model_aliases:
  glm-5.3:
    model: glm-5.3
    provider: custom:zuz8        # custom:<slug> — slug MUST be registered in custom_providers
    base_url: https://zuz8.xyz/v1
    api_key: sk-...              # per-model key; do NOT reuse other providers' key
  zuz8-sol:
    model: gpt-5.6-sol
    provider: custom:zuz8
    base_url: https://zuz8.xyz/v1
    api_key: sk-...
```

- `provider` uses `custom:<slug>` form. The slug must exist in the top-level
  `custom_providers:` list with its own `base_url` (and optional `api_key`).
- Each alias carries its OWN `api_key` — never share one key across models
  that bill separately (opus vs gpt vs glm keys are usually distinct).
- Do NOT set a conflicting `base_url`/`api_key` at `model:` top level when
  `model.provider` points at a `custom:<slug>`; let the provider entry supply
  it, or real provider-level config can shadow the alias.

## Verify without restarting

`hermes model` needs an interactive TTY (fails under pipe). Instead
introspect the parser directly (works from a normal shell):

```python
import sys, os
sys.path.insert(0, "/usr/local/lib/hermes-agent")
sys.path.insert(0, "/usr/local/lib/hermes-agent/venv/lib/python3.11/site-packages")
os.environ.setdefault("HERMES_HOME", "/root/.hermes")
from hermes_cli.model_switch import resolve_alias, _ensure_direct_aliases, DIRECT_ALIASES
_ensure_direct_aliases()
for n in ["glm-5.3", "zuz8-sol"]:
    da = DIRECT_ALIASES.get(n)
    print(n, "->", da.model, da.provider, da.base_url, da.api_key[:8])
    print("resolve:", resolve_alias(n, "custom:kugua"))
```
Expected: `resolve_alias` returns `('custom:zuz8', '<model>', '<alias>')` and
the DIRECT_ALIASES entry carries the right base_url + api_key. If it shows
the OLD provider (e.g. kugua) or a bare alias name as the model, the entry is
in the wrong store or model.provider is misaligned.

Then curl the endpoint to prove the key+model actually respond:

```bash
curl -s -m 40 -X POST "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"<model>","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
```
Give `-m 40`+ — reasoning models (gpt-5.6-sol) often exceed 20s and a short
timeout yields an empty body that looks like a failure.

## Switching models

Session-scoped and instant: send `/model <alias>` in chat. It stores a session
override (check `_session_model_overrides`) — no gateway restart needed.

To change the GLOBAL default: set top-level `model.provider` AND
top-level `model.default` (the plain model string, NOT `provider/model`), then
the running gateway picks it up only after a restart.

## Restarting the gateway

`hermes gateway restart`, `systemctl restart/stop hermes-gateway.service`, and
`systemctl kill` on the gateway PID are ALL blocked from inside the gateway
process (the tool layer refuses gateway-lifecycle commands to prevent
SIGTERM-respawn loops). Cron jobs carrying `restart` are blocked too.
So a restart must be run from a shell OUTSIDE the gateway. For switching
models you almost never need it — use `/model <alias>`.

## Diagnostics quick table

| Symptom | Cause | Fix |
|---|---|---|
| `/model foo` shows old provider (kugua) + bare name | alias in wrong store or `model.provider` misaligned | move to top-level `model_aliases:` dict |
| `unsupported model: <alias>` | model name sent literally, key/base_url not applied | top-level dict entry |
| Gateway restart blocked | inside gateway process | run outside / use /model |
| curl empty body for reasoning model | short timeout | `-m 40`+ |
