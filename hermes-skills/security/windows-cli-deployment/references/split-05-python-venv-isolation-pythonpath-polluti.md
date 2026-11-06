## Python Venv Isolation (PYTHONPATH Pollution)

When running Python-based CLI tools (installed via `uv sync` or `pip install`) in the same environment as Hermes Agent, the `PYTHONPATH` environment variable leaks Hermes's venv `site-packages` into the tool's Python process. This causes **version conflicts** when the tool depends on different versions of packages (pydantic, openai, etc.) than what Hermes uses.

### Symptom

```
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```

This happens because `sys.path` lists Hermes's site-packages FIRST:

```
C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages  ← PROBLEM
C:\Users\Administrator\Desktop\tool\.venv\Lib\site-packages                       ← Expected
```

### Fix: Clear PYTHONPATH

```bash
PYTHONPATH="" .venv/Scripts/python.exe -m tool.module --help
```

This only works when running the tool's **own venv Python** directly (not the system Python). The tool's `.venv/Scripts/python.exe` should have its own isolated site-packages.

### Verify

```bash
PYTHONPATH="" .venv/Scripts/python.exe -c "import sys; print([p for p in sys.path if 'hermes' in p.lower()])"
# Should print [] (empty)
```

### For uv-installed tools

```bash
cd ~/Desktop/tool
uv sync                                    # Creates .venv/
PYTHONPATH="" uv run --frozen tool --help  # OR
PYTHONPATH="" .venv/Scripts/python.exe -m tool --help
```

### Pitfall: --frozen vs uv run

`uv run --frozen` uses the existing lock file without syncing. `uv run` without --frozen may try to sync again. If the lock file is up to date, either works, but `--frozen` is faster and avoids accidental dependency changes.

