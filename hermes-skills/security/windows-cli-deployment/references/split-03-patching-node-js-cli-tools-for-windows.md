## Patching Node.js CLI Tools for Windows

Linux-originated Node.js tools (ESM modules) frequently have these Windows-incompatible patterns:

### 1. ESM `import()` with Absolute Paths

**Problem**: Dynamic `import('C:\\path\\to\\sdk')` fails with _"Received protocol 'c:'"_ because Node.js ESM interprets `C:` as a URL scheme.

**Fix**: Convert Windows absolute paths to `file:///` URLs:

```javascript
// Before (broken on Windows):
const url = cand.startsWith('/') ? 'file://' + cand : cand;

// After (works on Windows):
let url = cand;
if (/^[a-zA-Z]:[\\\\/]/.test(cand)) {
  url = 'file:///' + cand.replace(/\\\\/g, '/');
} else if (cand.startsWith('/')) {
  url = 'file://' + cand;
}
```

**Variant: Leading-backslash paths (`\\C:\\...`)**

On Windows, `new URL(import.meta.url).pathname` returns paths like `/C:/Users/...`. When this goes through `path.join()` with relative segments, the result can be `\\C:\\Users\\...` (leading backslash before drive letter). The regex `/^[a-zA-Z]:/` won't match because the string doesn't start with the drive letter.

**Fix**: Strip leading backslash(es) before testing:

```javascript
// Handle \C:\... variant
const clean = cand.replace(/^\\\\+/, '');
if (/^[a-zA-Z]:/.test(clean)) {
  url = 'file:///' + cand.replace(/\\\\/g, '/').replace(/^\\\\/*/, '');
}
```

Or more robustly, combine into a single check:

```javascript
// Windows absolute path fix — handles C:\, \C:\, and /C:/ formats
let url = cand;
const normalized = cand.replace(/^[\\\\/]+/, '');
if (/^[a-zA-Z]:/.test(normalized)) {
  url = 'file:///' + cand.replace(/\\\\/g, '/').replace(/^[\\\\/]+/, '');
} else if (cand.startsWith('/')) {
  url = 'file://' + cand;
}
```

### 2. Hardcoded Unix SDK Paths

Many tools hardcode SDK locations like `/data2/code/...`. These need to be replaced with path-relative lookups:

```javascript
// Instead of hardcoded Linux paths, resolve relative to the script:
import { fileURLToPath } from 'node:url';
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const sdkPath = path.join(scriptDir, 'node_modules', '@anthropic-ai', 'sdk', 'index.mjs');
```

### 3. Workflow Resolution Dirs

Tools that look for workflow files search in:

1. `project/.claude/workflows/`
2. `~/.claude/workflows/`
3. `~/.cc-wasm/workflows/`

On Windows, `os.homedir()` resolves correctly to `C:\Users\<username>`. Ensure workflow `.js` files are copied there:

```python
import shutil, os
dst = os.path.expanduser('~/.claude/workflows')
os.makedirs(dst, exist_ok=True)
for f in os.listdir(src_dir):
    if f.endswith('.js'):
        shutil.copy2(os.path.join(src_dir, f), os.path.join(dst, f))
```

### 4. npm Install Works Fine

`npm install` works normally on Windows via cmd.exe. The SDK gets installed to `node_modules/` correctly. The problems are only in how the tool's own source code *references* those modules.

