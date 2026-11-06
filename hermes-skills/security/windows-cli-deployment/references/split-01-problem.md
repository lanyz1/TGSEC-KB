## Problem

On Windows, Hermes Agent's `terminal` tool requires **Git for Windows** (Git Bash). If Git Bash is not installed (or `HERMES_GIT_BASH_PATH` is not set), `terminal` and `read_file` fail with:

```
Command execution failed: RuntimeError: Git Bash not found.
```

This blocks extraction, file inspection, npm install, and execution of CLI tools shipped as source.

