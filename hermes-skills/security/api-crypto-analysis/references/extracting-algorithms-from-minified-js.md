# Extracting Algorithmic Logic from Minified/Obfuscated Client-Side JS

## When to Use This Technique

Use when a web tool's functionality depends on client-side algorithms (data generation, validation, formatting) that are embedded in minified JS, and you need to understand or reproduce the logic without running the full page context.

**Not crypto-specific** — this covers non-crypto algorithms: checksums, data generators, formatters, IBAN generators, address validators, etc.

## Step-by-Step Method

### 1. Identify JS Source Files

Check which scripts the page loads:

```javascript
// In browser console (if not restricted):
Array.from(document.querySelectorAll('script')).map(s => s.src || s.type || s.id)
```

Or view page source HTML to find `<script src="...">` tags.

### 2. Download Source Files Directly (When Browser Console is Restricted)

If the browser console blocks `fetch()` or other network operations (common security restriction), download JS files with `curl`:

```bash
# Download each JS file identified in step 1
curl -s "http://target.com/static/app.js" > app.js

# Check file sizes to prioritize analysis:
# - Large files (>100KB) are likely the interesting ones
# - Vendor libs (jQuery, lodash, React, chance.js) can be skipped
ls -lh *.js
```

### 3. Find the Key Functions

Search for function definitions and key variable names:

```bash
# Find all function definitions (named and assigned)
grep -n "function [a-zA-Z]" app.js | head -30

# Find specific patterns based on the tool's behavior
grep -n "function build\|function calc\|function gen\|function check" app.js

# Find algorithm indicators
grep -n "checksum\|mod\|hash\|IBAN\|validate\|generate\|random" app.js
```

### 4. Extract Target Functions

Once you've identified the target function name and line numbers, extract just that section:

```bash
# Extract lines 150-400 (the function + surrounding context)
sed -n '150,400p' app.js
```

For the `buildIbans` function specifically (which may contain a large switch/case statement):

```bash
# First find the function
grep -n "function buildIbans" app.js
# → 341:function buildIbans(country_input) {

# Find where it ends (next function definition or end of file)
grep -n "function \|^var \|^const " app.js | awk -F: '$1 > 341 {print; exit}'

# Extract just that function
sed -n '341,END_LINEp' app.js
```

### 5. Identify Algorithm Patterns

Common patterns to look for in data-generation/minification JS:

| Pattern | What It Is | Example |
|---------|-----------|---------|
| Static lookup tables | Country codes, lengths, letter-to-number maps | `var iso_abbreviations = {Germany:"DE", ...}` |
| Weight/table arrays | Checksum calculation tables | `var d = [[0,1,2,...], ...]` — Damm algorithm or Verhoeff |
| Letter-to-digit maps | For MOD 97 or similar | `var letter_map = {A:10, B:11, ...}` |
| Switch/case by country | Different generation rules per locale | `switch(country_input) { case "Germany": ... }` |
| Fixed string prefixes | Bank codes, routing numbers | `"50010517"` (German bank code) |
| `chance.string()` | Random string generation (Chance.js library) | `num_gen3(10)` = 10 random digits |
| String prototype extensions | Custom checksum methods | `String.prototype.bankAccountKey = function() { ... }` |

### 6. Trace Function Composition

Data generation tools often compose several helper functions. Identify the call chain:

```
display()                    # UI entry point (functions.js)
  → buildIbans(country)      # Dispatcher (mapp4.js)
    → calcChecksum(ISO, part) # MOD 97-10 core (mapp4.js)
      → replaceChars(str)     # Letter→digit conversion
      → bankAccountKey()      # MOD 97 modulus
```

### 7. When Browser Tools Are Blocked

Some pages block `fetch()`/`XMLHttpRequest` from console (security sandbox). Recovery options:

1. **curl for JS files** (primary) — Download the same JS files the browser loads
2. **curl for page HTML** — Get the full HTML including inline scripts
3. **Save page as** — Use browser "Save as" to get rendered HTML
4. **View page source** — Right-click → View Page Source, find inline `<script>` blocks

### 8. Document the Algorithm

For each country/case, document:

- **IBAN length** (e.g., Germany: 22)
- **Fixed prefix / bank code** (e.g., Germany: "50010517")
- **Variable part** (e.g., 10 random digits)
- **Checksum algorithm** (MOD 97-10)
- **Edge cases** (e.g., Italy uses a letter CIN character before the numeric part)

### 9. Verify Reproduction

Test your understanding by either:
- Reading the function logic and verifying with known examples
- Using the original tool to generate a value, then manually applying your documented algorithm to confirm it matches
- Running the extracted JS logic locally with Node.js against known inputs

### Example: Germany IBAN from randomiban.com

```javascript
// Source: http://randomiban.com/static/mapp4.js (case "Germany")
// Algorithm:
//   1.  Bank code = "50010517" (fixed, 8 digits)
//   2.  Account  = random 10 digits  (IBAN_length 22 - 12)
//   3.  Raw      = bankCode + accountNumber
//   4.  Checksum = 98 - (mod97(lettersToDigits(raw + "DE" + "00")))
//   5.  IBAN     = "DE" + checksum + raw  (22 chars total)

// Helper: convert letters to numbers (A=10, B=11, ..., Z=35)
// MOD 97: IBM's standard ISO 13616 bankAccountKey algorithm
```

## Tools Required

| Tool | Purpose |
|------|---------|
| `curl` | Download JS files directly |
| `grep` | Find function definitions, key patterns |
| `sed` | Extract specific line ranges |
| `wc -l` | Check file sizes, line counts |
| Node.js (optional) | Run extracted JS locally for verification |

## Common Pitfalls

- **Don't assume all interesting logic is in one file** — the tool may split logic across `functions.js`, `mapp4.js`, `countries.js`, etc.
- **Don't skip vendor libs** — `chance.js` provides `chance.string()` which is the random generator for many tools. Know what it does.
- **Don't ignore inline scripts** — the HTML page's `<script>` blocks may contain country lists, API endpoints, or configuration data not in the external JS files.
- **Obfuscated JS** — If functions are renamed (single-letter names, hex-encoded strings), search for **data structure patterns** (arrays, lookup tables) rather than function names. The data structures are harder to obfuscate than control flow.
- **Large switch/case blocks** — For country-specific tools, the entire switch/case may be one function spanning hundreds of lines. Extract it in chunks with `sed` or pipe to a file.
- **String pool from obfuscation** — Extremely obfuscated JS (like JSFuck or string-encoded) won't yield useful patterns with grep. Fall back to runtime analysis (set breakpoints, watch variables in browser dev tools).
