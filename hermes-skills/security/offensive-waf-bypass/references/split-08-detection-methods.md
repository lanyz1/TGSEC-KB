## Detection Methods

```mermaid
flowchart LR
    A[WAF Detection Methods] --> B[Control Page Analysis]
    A --> C[HTTP Header Inspection]
    A --> D[Cookie Analysis]
    A --> E[Route Examination]
    A --> F[JavaScript Object Analysis]

    B --> B1[Block Pages]
    B --> B2[Challenge Pages]
    B --> B3[CAPTCHA Systems]

    C --> C1[Custom Security Headers]
    C --> C2[Server Headers]
    C --> C3[CDN Markers]

    D --> D1[WAF-specific Cookies]
    D --> D2[Challenge Cookies]

    E --> E1[CDN Paths]
    E --> E2[WAF Asset Routes]

    F --> F1[Protection Objects]
    F --> F2[Challenge Scripts]

    style A fill:#f96,stroke:#333,stroke-width:2px,color:#333
```

1. **Inspect Control Pages** - Many WAFs display specific pages when blocking access
2. **Analyze HTTP Headers** - Check response headers for WAF-specific indicators
3. **Examine Cookies** - WAFs often set specific cookies (e.g., cf_clearance for Cloudflare)
4. **Look for Specific Routes** - e.g., /cdn-cgi/ for Cloudflare
5. **Check JavaScript Objects** - WAFs inject specific JS objects (e.g., `\_cf_chl_opt`)
6. **JA3/JA4/TLS Fingerprints** - Compare your client’s TLS fingerprint with common browser fingerprints; mismatches are often blocked.
7. **HTTP/2/3 Support** - Identify protocol negotiation; some WAF policies differ by protocol.

### Fingerprinting WAFs

Some specific fingerprints of common WAFs:

- **Apache Generic**: Writing method type in lowercase (e.g., `get` instead of `GET`)
- **IIS Generic**: Using tabs before method (e.g., `    GET /login.php HTTP/1.1`)
- **Cloudflare**: Challenge pages with JavaScript verification
- **ModSecurity**: Specific error messages and block pages
- **AWS WAF**: AWSELB cookies and specific headers
- **Fastly Next‑Gen WAF**: `fastly-debug-*` headers (when enabled), service IDs in responses
- **Cloudflare Bot Fight Mode/AI WAF**: presence of Turnstile, managed challenge flows, Bot Management headers

