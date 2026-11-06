---
name: hermes-model-providers
description: "Use when adding custom models/keys in Hermes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, config, models, providers, aliases, openai-compatible, multi-model]
---

# Hermes Model Providers

Adding a third-party OpenAI-compatible endpoint (e.g. `https://zuz8.xyz/v1`, any aggregator/gateway)
to Hermes so `/model <name>` actually switches base_url **and** API key — and does NOT leak the
previously-active provider's key or base_url.

## THE GOTCHA (costs a session if you miss it)

`hermes config set model.aliases.<name> '<json-dict>'` writes into **`model.aliases`**
(under `model:`). In Hermes <= v0.21, `_load_direct_aliases()` treats `model.aliases` as
**STRING-only** entries:

```python
# hermes_cli/model_switch.py
simple_aliases = model_section.get("aliases")
for name, value in simple_aliases.items():
    if not isinstance(value, str) or not value.strip():
        continue   # <- dict values are silently SKIPPED
```

So a dict alias (with base_url/api_key) is dropped, `/model <name>` falls back to treating `<name>`
as a raw model id against the CURRENT provider, and you get:

```
HTTP 400 Unsupported model: glm53. Allowed: deepseek-v4-flash   (model_not_found)
gateway log: base_url=https://ai.kugua.shop/v1 model=glm53
```

## WORKING CONFIG (top-level `model_aliases:` — dict, put per-model key here)

Edit `~/.hermes/config.yaml` directly (python/yaml) — do NOT rely on `config set` for the dict form.

```yaml
custom_providers:
  - name: zuz8
    base_url: https://zuz8.xyz/v1

model_aliases:
  glm-5.3:
    model: glm-5.3
    provider: custom:zuz8
    base_url: https://zuz8.xyz/v1
    api_key: sk-ff2...
  glm-5.3-flash:
    model: glm-5.3-flash
    provider: custom:zuz8
    base_url: https://zuz8.xyz/v1
    api_key: sk-ff2...
  zuz8-sol:
    model: gpt-5.6-sol
    provider: custom:zuz8
    base_url: https://zuz8.xyz/v1
    api_key: sk-8de...
```

Key rules:
- **`provider` MUST be `custom:<slug>`** (e.g. `custom:zuz8`), where `<slug>` is an entry in the
  top-level `custom_providers` list. Plain `custom` does not bind the base_url reliably.
- Each alias carries its OWN `base_url` + `api_key`. Hermes resolves the key from the alias host,
  never from the previously-active provider → **no key bleed**. Good for "opus and gpt keys differ".
- Keep the `custom_providers` entry so the picker/catalog sees the endpoint.

## Verify after writing

```bash
python3 scripts/verify_model_alias.py   # prints DIRECT_ALIASES + resolve_alias() for each alias
# then curl the endpoint for each model to confirm it actually answers
curl -s -m 60 https://<host>/v1/chat/completions -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"<model>","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
```

Note `hermes model` requires a TTY (fails via pipe). Use the python probe instead. Reasoning models
that echo `reasoning_content` can be slow — raise curl `-m` (60s+) so you don't misread a timeout as
"model not found".

## Setting a model as the DEFAULT

`model.default` is a BARE model name, paired with `model.provider` = `custom:<slug>`:

```yaml
model:
  provider: custom:zuz8
  default: glm-5.3-flash
```

Do NOT write `custom:zuz8/glm-5.3-flash` into `model.default` — the slash-form is only legal on
aggregators (openrouter) and `custom:`-prefixed providers, but it makes provider-vs-model ambiguous
and contradicts `model.provider`. Keep `default` bare.

Also clear leftover provider-level fields when changing provider via python/yaml:
`model.base_url` and `model.api_key` from the OLD provider conflict with the new one — drop them
(the active `custom:<slug>` pulls base_url/key from `custom_providers` and the alias).

**A running gateway does NOT hot-reload `model.default`.** After editing config, the change only
takes effect when the gateway restarts: `systemctl restart hermes-gateway` (PID 1 parent, maintained
by `hermes-gateway.service`). `/model <alias>` in a live session is session-scoped and does NOT
update the global default.

## Switching

In chat: `/model <alias-name>`. In CLI: `hermes chat -m <alias-name>`. With no `--global` it is
session-scoped; default persists in `model.default` and needs a gateway restart to apply.

See `references/hermes-alias-gotcha.md` for the full diagnostic transcript / root-cause lines,
and `scripts/verify_model_alias.py` to re-run the probe.
