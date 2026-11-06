## Verification Checklist

After deployment, verify with a **prepare/dry-run** mode (no API call):

```bash
# For wf-engine style tools:
node tool.mjs --project <dir> --name <workflow> --prepare

# For engine.mjs style tools:
node src/engine.mjs --project <dir> --script <workflow.js> --prepare
```

Exit code 0 + printed workflow metadata = success.
Exit code 2 + "no saved workflow" = need to copy workflow files to expected directory.

