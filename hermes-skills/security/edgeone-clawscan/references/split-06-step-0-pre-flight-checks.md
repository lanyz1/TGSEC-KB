## Step 0: Pre-flight Checks

Before running any scan command, silently perform the following two checks and
abort with a clear user-visible warning if either fails.

**0.1 — Verify `openclaw` binary on PATH**

```bash
which openclaw
```

If the binary is not found or the path looks unexpected (e.g. a non-standard
location), output a warning and ask the user to confirm the binary is the
intended OpenClaw installation before continuing.

**0.2 — Confirm environment is not a production Gateway**

Inspect `openclaw.json` to determine the configured Gateway endpoint. If the
endpoint appears to be a production URL (non-localhost, non-test domain), output
the following warning and wait for explicit user confirmation before proceeding:

> ⚠️ **Production Gateway Detected**
> The locally configured Gateway appears to be a production endpoint.
> Running `--deep` will probe it live. Verify your exposure and access-control
> settings before continuing, or re-run in an isolated/test environment.
> Reply "confirm" to proceed, or "cancel" to abort.

