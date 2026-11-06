## Attack Surface Signals

**Response-header fingerprints (any one is sufficient — usually multiple co-occur):**
```
SPRequestGuid: <GUID>                           (always — anonymous and authenticated)
X-MS-InvokeApp: 1; RequireReadOnly              (SharePoint web request)
X-SharePointHealthScore: 0                      (SharePoint specific)
SPIisLatency: <ms>                              (SharePoint internal timing)
SPRequestDuration: <ms>                         (SharePoint request duration)
MicrosoftSharePointTeamServices: [REDACTED_IP]      (often stripped by ELB — but if present, exact version)
X-Forms_Based_Auth_Required: <login URL>        (Forms-auth zone indicator)
X-Forms_Based_Auth_Return_Url: <return URL>     (Forms-auth zone indicator)
X-MSDAVEXT_Error: 917656; Access denied...      (WebDAV extension active)
DAV: 1, 2                                       (WebDAV verbs supported)
Set-Cookie: ASP.NET_SessionId=...               (always — IIS session)
Set-Cookie: FedAuth=...; rtFa=...               (claims-mode auth)
Set-Cookie: WSS_FullScreenMode=...              (SharePoint UI mode)
```

**URL / path fingerprints:**
```
/_layouts/15/                  (SP2013+ layouts root — SP2010 used /_layouts/ without the 15)
/_layouts/14/                  (legacy SP2010 — almost EoL since 2020-10-13)
/_layouts/16/                  (some SP2019 / SPE)
/_vti_bin/                     (FrontPage-RPC + SOAP services)
/_vti_pvt/                     (FrontPage-RPC config — usually 403)
/_vti_inf.html                 (almost always anonymous; contains FPVersion banner)
/_api/                         (modern REST API)
/_api/$metadata                (OData metadata — often anonymous + large)
/_api/contextinfo              (FormDigest issuer — POST only)
/_catalogs/                    (site catalogs: masterpage, wp, lt, theme, solutions)
/_catalogs/users/simple.aspx   (user list — usually 403)
/_layouts/15/start.aspx        (anonymous landing — leaks version)
/_layouts/15/ToolPane.aspx     (web part editor — ToolShell sink)
/_layouts/15/Picker.aspx       (people/list picker — SafeControl recon)
/_layouts/15/download.aspx     (SP-internal file resolver — NOT outbound SSRF)
/_layouts/15/Authenticate.aspx (forms-auth redirector)
/_layouts/15/SignOut.aspx      (logout)
/_layouts/15/error.aspx        (error page — anonymous)
/_layouts/15/AccessDenied.aspx (denied page — anonymous)
/_layouts/15/scriptresx.ashx?culture=en-us&name=core    (resource bundle leak)
/_layouts/15/<Customer>/       (custom-branding modules — see Methodology step 8)
/_vti_bin/Authentication.asmx  (THE legacy login bypass — see hunt-auth-bypass Legacy-Protocol Matrix)
/_vti_bin/SharedAccess.asmx    (often anon-readable)
/_vti_bin/lists.asmx           (auth-required on hardened farms)
/_vti_bin/sites.asmx           (auth-required on hardened farms)
/_vti_bin/sts/                 (Security Token Service — usually 302 to error)
/sites/<name>/                 (site collections)
/personal/<user>/              (MySite / OneDrive-for-Business)
```

**Body signals (in HTML responses):**
```
<meta name="GENERATOR" content="Microsoft SharePoint" />
RegisterSod("...","/_layouts/15/...");                    (Script-on-demand registration)
var g_initUrl='';                                          (start.aspx MDS state)
__REQUESTDIGEST                                            (CSRF token — leaks even to anon if endpoint mis-configured)
__VIEWSTATEENCRYPTED=""                                    (Sign-only ViewState — see hunt-aspnet)
"LibraryVersion":"15.0.X.XXXX"                             (in _api/contextinfo response)
Version:15, webPermMasks:{High:0,Low:                      (in start.aspx body)
HelpWindowKey('WSSEndUser_troubleshooting                  (anonymous error.aspx body)
```

**Tech-stack signals:**
- `Server: Microsoft-IIS/10.0` + paths starting with `/_layouts/15/` → SharePoint 2013/2016/2019/SE
- AWS ELB / ALB in front of SharePoint → cross-node ViewState MAC issues possible (see hunt-aspnet)
- `WWW-Authenticate: NTLM` on `/_api/web/CurrentUser` → dual-auth (Forms + NTLM); use `hunt-ntlm-info` for AD-topology disclosure
- `*.test.<customer>.tld` → test/staging mirror of production SharePoint; data often mirrored from prod

---

