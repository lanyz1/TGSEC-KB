## Workaround: Python execute_code as Surrogate Shell

Use `execute_code` with Python's `subprocess` module to run shell commands, and Python's built-in `os`/`shutil`/`zipfile` for file operations.

### File System Ops

```python
import os, shutil, zipfile

# Extract zip
with zipfile.ZipFile(path, 'r') as zf:
    zf.extractall(dest_dir)

# List files
for root, dirs, files in os.walk(dest_dir):
    ...

# Copy/remove
shutil.copytree(src, dst)
shutil.rmtree(path)
```

### Running Shell Commands

```python
import subprocess

def run_cmd(cmd, cwd=None, timeout=30):
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=cwd, shell=True, timeout=timeout
        )
        return r.stdout, r.stderr, r.returncode
    except Exception as e:
        return "", str(e), -1
```

**IMPORTANT**: Use `shell=True` and pass the command as a single string (cmd.exe-style). On Windows, `shell=False` with a list often fails for CLI tools.

### Reading Files

```python
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
```

