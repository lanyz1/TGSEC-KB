## Python Sandbox Caveats

Hermes's `execute_code` runs Python in an isolated sandbox:

- **Imports don't persist between cells** — each `execute_code` call is a fresh process. Always re-import everything you need.
- **Stdout is the output channel** — `print()` is how data returns.
- **`subprocess` with `shell=True`** runs via cmd.exe, which has access to the same PATH as the Hermes app.
- **Node.js/npm/Git** — check their actual location with `where node` / `where npm` via subprocess, not `shutil.which()` (which may not search all PATH locations in the sandbox context).

