## 11. Identity Fabric Mapping

An organization's IdP/SSO posture is a high-value target: compromise the identity fabric and you don't need to break into individual apps. Map it methodically.

### 11.1 Subdomain prefix enumeration

Probe these prefixes against the target's root domain (and any sibling brand domains discovered):

```
auth.{domain}
login.{domain}
sso.{domain}
idp.{domain}
iam.{domain}
identity.{domain}
accounts.{domain}
oauth.{domain}
```

Plus generic OIDC discovery on every alive subdomain:
```
{any-host}/.well-known/openid-configuration
```

### 11.2 Microsoft Entra (Azure AD)

- **OIDC metadata + tenant GUID extraction** — fetch `https://login.microsoftonline.com/{tenant-or-domain}/.well-known/openid-configuration`. The `issuer` field returns a URL containing the tenant GUID (8-4-4-4-12 hex format). Tenant GUID + domain = stable tenant fingerprint.
- **getuserrealm.srf** — `https://login.microsoftonline.com/getuserrealm.srf?login=<user>@<domain>` returns NameSpaceType: `Managed` (cloud-native), `Federated` (on-prem ADFS / external IdP), or `Unknown`. Detectability: low.
- **Autodiscover v2** — `https://autodiscover-s.outlook.com/autodiscover/metadata/json/1` POST with email; detects tenant membership.
- **GetCredentialType** (deep-mode user-enum) — `https://login.microsoftonline.com/common/GetCredentialType` POST `{"username": "<email>"}`. Response indicates whether email exists in tenant. Detectability: medium. Cap attempts at 20 per tenant.

### 11.3 Okta

- **Org slug derivation** — derive candidate slugs from subdomains + root domain stem; Okta tenants live at `<slug>.okta.com` (or `<slug>.oktapreview.com`).
- **OIDC fingerprint** — `https://<slug>.okta.com/.well-known/openid-configuration`.
- **/api/v1/authn user-enum** (deep-mode) — POST `{"username": "<email>", "password": "invalid"}`. 400 vs 401 response code indicates user existence. Detectability: medium. Cap at 20 per tenant.

### 11.4 ADFS

- **Passive fingerprint** — GET `https://{domain}/adfs/idpinitiatedsignon.aspx` → 200 indicates ADFS present.
- **Active mex endpoint** (deep-mode) — `https://{domain}/adfs/Services/Trust/mex` returns SOAP metadata.

### 11.5 Google Workspace

- `https://{domain}/.well-known/openid-configuration` — Google-hosted-domain customers expose discovery endpoints with characteristic issuer/JWKS URIs.
- MX records pointing to `*.googlemail.com` / `aspmx.l.google.com` is a strong Google Workspace signal.

### 11.6 Generic OIDC (Keycloak / Auth0 / Ping / OneLogin / Duo)

- Probe every alive subdomain for `/.well-known/openid-configuration`.
- The `issuer` and `authorization_endpoint` fields fingerprint the IdP product.
- `*.auth0.com`, `*.onelogin.com`, `*.pingone.com`, `*.duosecurity.com` patterns are characteristic.

### 11.7 SAML metadata

Probe these paths on every alive webapp:

```
/saml/metadata
/FederationMetadata/2007-06/FederationMetadata.xml
/federationmetadata/2007-06/federationmetadata.xml
/simplesaml/saml2/idp/metadata.php
/auth/saml2/metadata
```

SAML metadata XML contains: `EntityID`, signing certs, `SingleSignOnService` URL, `NameIDFormat`.

### 11.8 AWS account-ID extraction

- **S3 bucket region header** — HEAD on a known target bucket returns `x-amz-bucket-region`; correlate with bucket-name entropy to infer account.
- **ARN regex in JSON / HTML responses** — search for `arn:aws:[a-z0-9-]+:[a-z0-9-]*:([0-9]{12}):` (the 12-digit AWS account ID is the capture group).
- **`AccountId` property in JS / API responses** — common in IAM-related error messages and CloudFormation outputs.
- **OAuth client_id leaks** — Google OAuth: `<digits>-<chars>.apps.googleusercontent.com`; MSAL: GUID in `clientId` property.

### 11.9 Output

Each discovered IdP becomes a `Service` asset with `attrs.product`, `attrs.tenant_id`, `attrs.discovery_endpoint`. Then in Stage 4, correlate with breach data: every compromised user under a discovered tenant becomes an SSO_EXPOSURE finding (CRITICAL — see §22.3).

### 11.10 Microsoft 365 Deep Surface

Beyond plain Entra fingerprinting, M365 exposes a wider attack surface that's worth enumerating in depth.

**Teams Federation:**

- `https://login.microsoftonline.com/<target-domain>/.well-known/openid-configuration` confirms tenant.
- Teams federation status: `https://teams.microsoft.com/api/mt/<region>/beta/users/<email>/externalsearchv3` (requires authenticated request from a federated tenant; useful for confirming whether external Teams chat is allowed).
- **External chat enabled** = soft-attack surface (vishing, smishing, "from-IT" pretexts via Teams chat).
- **Open Federation** (any tenant can chat) is the default; check whether the target restricted it.

**SharePoint subdomains:**

- `<target-stem>.sharepoint.com` — main tenant SharePoint.
- `<target-stem>-my.sharepoint.com` — OneDrive-for-Business URLs (per-user personal sites).
- `<target-stem>-admin.sharepoint.com` — SharePoint admin center (auth-required, but presence confirms tenancy).
- Where `<target-stem>` is derived from the company name (often the part before `.com`).

**OneDrive personal site enumeration:**

- Per-user OneDrive URL: `https://<target-stem>-my.sharepoint.com/personal/<user_email_with_underscore>/Documents/`.
- Replace `@` with `_` and `.` with `_` in the email (e.g., `<EMAIL-REDACTED>` → `alice_acme_com`).
- Authenticated probe; useful for confirming whether the OneDrive personal site has been provisioned (which itself is a presence indicator).

**M365 OAuth client_id discovery:**

- Many internal apps register OAuth client_ids in Entra. Search JS bundles, mobile-app strings, and API responses for `client_id=<GUID>` patterns.
- Microsoft's well-known first-party client_ids (for Office, Graph, etc.) are documented; finding non-Microsoft GUIDs reveals custom internal apps.
- The endpoint `https://login.microsoftonline.com/<tenant>/v2.0/.well-known/openid-configuration` lists supported endpoints; some tenants leave `device_authorization_endpoint` enabled (device-code phishing target).

**Power Platform / Power Apps:**

- `https://make.powerapps.com/environments` (auth-required); environment IDs sometimes leak in URLs.
- `*.crm.dynamics.com` (Dynamics 365 / Power Apps default URLs).
- `*.azurewebsites.net` for App Service deployments.

**M365 OAuth misconfig findings to look for:**

- `device_authorization_endpoint` enabled on `common` tenant (device-code phishing target) → **MEDIUM** (operational risk; not directly exploitable but enables attack).
- Custom OAuth app with `Public client` flow enabled and broad scopes (offline_access, Mail.Read, Files.Read.All) → **HIGH** if app is approved for the tenant.
- Multi-tenant OAuth app published by the target (others can consent) → check whether scopes include sensitive Graph permissions.

**Detectability:** all M365 endpoint probes log to Entra sign-in logs / audit logs (medium-low for fetch-only; medium for any auth attempt).

---

