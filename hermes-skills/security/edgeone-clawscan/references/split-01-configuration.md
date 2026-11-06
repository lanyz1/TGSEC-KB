## Configuration

`AIG_BASE_URL` (optional) — base URL for the AI-Infra-Guard API.
Defaults to `https://matrix.tencent.com/clawscan` (the public Tencent endpoint
declared in the `external_requests` metadata above).

**Privacy / air-gapped environments**: to avoid sending skill names, source
labels, or version strings to the public Tencent host, use one of: (1)
`AIG_BASE_URL` pointing at a self-hosted AI-Infra-Guard you operate, or (2)
`AIG_CLOUD_LOOKUP=off` so **no** A.I.G HTTPS request runs (fully local Step 2
and Step 3). Curl uses
`${AIG_BASE_URL:-https://matrix.tencent.com/clawscan}` only when cloud lookup
is enabled.

```bash
export AIG_BASE_URL=https://your-self-hosted-aig.example.com/clawscan
export AIG_CLOUD_LOOKUP=off
```

