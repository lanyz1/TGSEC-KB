## 39. Attack-Path Hint Patterns

When emitting a HIGH/CRITICAL API endpoint finding (score ≥ 70), include a one-sentence `attack_path_hint` in evidence so the operator knows where to start exploiting. Templates:

| Trigger | Attack-path hint |
|---|---|
| Unauth POST / PUT / DELETE | *"Unauthenticated {method} {path} — try IDOR + privilege escalation; check whether numeric IDs are sequential or guessable."* |
| Open GraphQL introspection | *"Open GraphQL introspection on {path} — enumerate mutations, look for `createUser`, `setRole`, `transferFunds`-shaped names; pivot to broken-auth or business-logic flaws."* |
| Reflected CORS + creds | *"Reflected CORS with credentials on {path} — host CSRF page on attacker-controlled origin; victim's browser will leak {sensitive-data-hint}."* |
| Wildcard CORS + sensitive | *"Wildcard CORS on {path} returning user-tied data without creds — exfiltrate via cross-origin fetch from any page victim visits."* |
| Verb tampering | *"Verb tampering: {hidden-method} allowed on documented-{visible-method}-only endpoint → likely missing-method-check authz bug; try {hidden-method} {path} with valid auth."* |
| API key in URL | *"API key in URL: `?{param}=...` — token leaks to access logs, browser history, Referer headers, third-party CDNs. Check Wayback / Google for cached copies."* |
| Schema leak in error | *"Schema leak in error response — framework signature `{framework}` exposed; map to known {framework} vulns and craft targeted payloads."* |
| Sensitive keyword | *"Path contains '{keyword}' — review for direct object reference, mass-assignment, or hidden admin functionality."* |
| Open RTDB Firebase | *"Open Firebase RTDB at https://{project}.firebaseio.com/.json — read everything, then test write at `/<random-key>.json` with PUT to gauge ACL scope."* |
| Listable cloud bucket | *"Listable {provider} bucket `{bucket}` — recursive object listing + content-type analysis; look for backups, logs, customer data, AWS keys in JSON configs."* |
| .git exposed | *"Exposed .git/config on {host} — reconstruct repository with git-dumper or githacker; full source history."* |
| .env exposed | *"Exposed .env on {host} — grep for `_KEY`, `_SECRET`, `_TOKEN`, `_PASSWORD`; validate all credentials read-only via §23 validators."* |
| /actuator/env | *"Spring Boot /actuator/env exposed — dump environment variables; look for `spring.datasource.password`, JWT secrets, cloud creds."* |
| /actuator/heapdump | *"Spring Boot /actuator/heapdump exposed — download HPROF, run `jhat` or VisualVM, search for cleartext secrets in heap strings."* |
| Open Elasticsearch | *"Open Elasticsearch on {host}:9200 — `/_cat/indices?v` for index list; sample documents from each high-value index; test write to `/test-idx/_doc` to gauge ACL."* |
| Open Redis | *"Open Redis on {host}:6379 — `INFO`, `KEYS *`, sample reads; check for write access via `CONFIG SET` then `BGSAVE` to write `authorized_keys`."* |
| Open MongoDB | *"Open MongoDB on {host}:27017 — `show dbs`, `show collections`, sample find queries; check user collection for password hashes."* |
| Subdomain takeover | *"CNAME for {host} points to unclaimed {provider} resource → register `{takeover-target}` on {provider} to serve content from {host}; pivot to phishing or content injection on the trusted domain."* |
| Open kubelet | *"Open kubelet on {host}:10250 — `GET /pods` to list; `POST /run/<ns>/<pod>/<container>` for in-container exec without K8s API auth."* |
| Open etcd | *"Open etcd on {host}:2379 — `etcdctl get / --prefix --keys-only` for full cluster state; secrets stored under `/registry/secrets/`."* |
| K8s API anonymous | *"Kubernetes API on {host}:6443 with anonymous-auth — `kubectl --server=https://{host}:6443 --insecure-skip-tls-verify get pods --all-namespaces`."* |
| Citrix unpatched | *"Citrix NetScaler version {ver} on {host} — vulnerable to CVE-{cve} (KEV-listed); see vendor advisory; do not exploit but flag for client immediate patching."* |
| F5 BIG-IP TMUI exposed | *"F5 BIG-IP TMUI on {host} reachable; CVE-2022-1388 / CVE-2023-46747 KEV applicable; advise immediate patching to vendor-released hotfix."* |
| VMware vCenter accessible | *"vCenter at {host} accessible without VPN; CVE-2021-21972 RCE if unpatched; check version banner."* |
| Cloud function URL unauth | *"AWS Lambda Function URL at {url} accessible anonymously — review IAM auth configuration; if unauthenticated by design, audit input validation aggressively."* |
| npm typosquat candidate | *"Package name `{candidate}` is unregistered + similar to target's published `{official}` — typosquat takeover risk; advise client to defensively register."* |
| DMARC missing/permissive | *"DMARC `p=none` on {domain} — spoof of `{anything}@{domain}` deliverable to recipients; recommend enforcement to `p=quarantine` or `p=reject` after observing reports."* |
| Live AI API key (Anthropic/OpenAI) | *"Validated `sk-{provider}-...` key with model access — quota cost can be exfiltrated; rotate immediately + audit usage logs in provider console."* |
| Public Slack invite link | *"Slack workspace invite link discoverable via search engine — anyone can join the workspace without approval; trivially access internal channels."* |
| Open Docker registry | *"Public Docker registry at {host} — `GET /v2/_catalog` lists images; pull and scan layers for embedded secrets."* |
| Telegram bot token live | *"Telegram bot token validated — `getUpdates` reveals bot recipients (admin chats); if `getMe` shows bot is in channels, full message read access."* |
| Sourcemap with `sourcesContent[]` | *"Sourcemap on {host} includes embedded original sources — full frontend code reconstructable; grep for inline secrets and internal hostnames."* |

---


---

