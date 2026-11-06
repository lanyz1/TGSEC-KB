## 49. Skill Self-Test

Drop these prompts into a fresh Claude session to verify the skill loads correctly.

1. *"What paths should I probe to find Swagger or OpenAPI specs on a webapp?"* → §16.1.
2. *"Give me the GraphQL introspection query I should POST."* → §16.2.
3. *"What are the high-risk ports to flag from a Shodan scan?"* → §16.3.
4. *"Show me the secret regex catalog."* → §17 (48 patterns) + §48 (runnable Python).
5. *"How do I score an API endpoint by attack interest?"* → §20.
6. *"Validate a leaked Postman API key — what URL?"* → §23.1.
7. *"Give me dorks for pastebin/gist/ghostbin leaks for a target."* → §18.3.
8. *"What endpoints fingerprint a Microsoft Entra tenant?"* → §22.1 + §22.8 for M365 deep.
9. *"How do I score whether a discovered Android app belongs to my target?"* → §21.
10. *"What attack-path hint when I find unauth POST on `/api/users`?"* → §39 (first row).
11. *"Curl one-liner to test for `/actuator/env`."* → §16.13.
12. *"Show me the GraphQL field-suggestion enumeration trick when introspection is disabled."* → §22.9.
13. *"Found a hard-coded JWT in JS. Walk me through full triage."* → §23.12 (JWT workflow).
14. *"Generate cloud bucket candidates for `<Client Brand Ltd>` with subdomains api/billing/hr."* → §16.8.
15. *"How do I find Microsoft 365 Teams federation status + SharePoint subdomains?"* → §22.8.
16. *"Probe paths for Citrix Netscaler / F5 BIG-IP / Pulse Secure."* → §16.16.
17. *"Find the origin behind Cloudflare on `target.example`."* → §16.15 + companion methodology §27.
18. *"What ports/paths probe for Kubernetes/etcd/kubelet exposure?"* → §16.18.
19. *"Audit `acme.com`'s SPF/DMARC for spoof feasibility."* → §16.14.
20. *"List wordlist sources for subdomain bruteforce + content discovery."* → §27.1.
21. *"Run reverse-DNS sweep across a /22 the target owns."* → §28.5.
22. *"Validate an OpenAI API key without burning quota."* → §23.6 + §23.12.
23. *"Find leaked secrets across npm/PyPI/Docker Hub for the target."* → §44.
24. *"How do I enumerate target employees on LinkedIn for a phishing list?"* → §41.
25. *"What's a Slack invite link enumeration technique?"* → §43.1.
26. *"What's the EPSS score and KEV status for CVE-2024-3400?"* → §29.2.
27. *"What modern AI API keys (Anthropic / OpenAI / HuggingFace / Cloudflare) match catalog patterns?"* → §17 rows 30–48.
28. *"Severity matrix for `android:debuggable=true` on prod app?"* → §40.
29. *"Install commands for the standard recon toolkit (subfinder/httpx/nuclei/etc.)?"* → §46.
30. *"For a healthcare engagement, what additional ports / protocols matter?"* → §47.1.
31. *"Pull HudsonRock breach corpus for `target.com` via direct API (no UI)."* → §15.0.1.
32. *"Run the full §16.14 email security audit from a Windows box (PowerShell)."* → §16.14 PowerShell parallel.
33. *"crt.sh just 502'd. What's the fallback chain?"* → §27.0.1.
34. *"Bulk IP → ASN lookup for 200 IPs without burning bgpview rate limit."* → §28.1 (Cymru bulk).
35. *"Common-prefix subdomain sweep for `target.example` covering vpn / api / staging / portal / intranet."* → §16.24.
36. *"Legacy mail (`mail.<domain>`) is NXDOMAIN today but breach corpus has employee URLs against it. What's the finding?"* → §15.2 legacy-mail-decommissioned pattern.
37. *"Confirm M365 tenancy when MX is wrapped by Mimecast (so MX doesn't reveal underlying mail platform)."* → §22.1 autodiscover IP correlation + §16.22 autodiscover-as-confirmation.
38. *"DMARC RUA points to `kdmarc.com` — what does that tell me?"* → §16.14 DMARC reporting-vendor table.
39. *"SharePoint HEAD probe returns HTTP 200. Does that mean anonymous access is granted?"* → §22.8 (no — tenant exists, not anonymous access; distinguish).
40. *"Wayback `*.js` query returned empty for a brochure-ware site. Pivot?"* → §16.23 legacy-app pivot (.asp / .php / .jsp / .cfm / .aspx).

---

