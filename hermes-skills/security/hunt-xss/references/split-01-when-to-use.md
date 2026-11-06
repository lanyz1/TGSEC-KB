## When to Use

Use when the target has any endpoint where user input is reflected in HTML output, processed by a JavaScript framework, or stored for later display. XSS is the foundational client-side vulnerability class — it enables session hijacking, data theft, phishing, and account takeover. Every form, search field, URL parameter, file upload, and user-controlled field is a candidate. Highest-value targets: admin panels, OAuth sign-in pages, markdown/wiki renderers, email templates, file upload endpoints (SVG/HTML), and help/documentation sites with looser security posture.

### ⚠️ CRITICAL: Presence ≠ Exploitation

**Reflection of HTML tags does NOT mean XSS is exploitable.** Modern frameworks escape text by default. Before calling a finding XSS, you MUST verify the sink:

| Framework | Default Behavior | XSS Possible Only With |
|-----------|-----------------|----------------------|
| React/JSX | Escapes all text | `dangerouslySetInnerHTML`, `innerHTML` on refs |
| Vue | Escapes `{{ }}` | `v-html` directive |
| Angular | Escapes `{{ }}` | `[innerHTML]` binding |
| Svelte | Escapes `{ }` | `{@html}` tag |
| Next.js RSC | Escapes JSX text | `dangerouslySetInnerHTML` in components |
| Plain HTML/JS | Does NOT escape | `innerHTML`, `document.write()`, `eval()` |

**XSS verification checklist:**
1. ✅ Payload is REFLECTED/STORED in response (presence)
2. ✅ Payload appears in a RENDERABLE context (sink check)
3. ✅ Payload EXECUTES in browser (proof of exploitation)

If step 1 passes but step 2 fails → **LOW: HTML storage without exploitable sink**. The React ecosystem alone prevents ~90% of apparent XSS because JSX auto-escapes.

**How to Check for Sinks:**
```bash
# In JS bundles — search for dangerous rendering patterns
grep -rEn 'dangerouslySetInnerHTML|innerHTML|outerHTML|v-html|\[innerHTML\]|\{@html\}|insertAdjacentHTML|document\.write\(|eval\(' /tmp/target_js/

# If NONE appear near the reflected field → NOT exploitable XSS
# If found → verify the specific field reaches that sink
```

