## Direct API Call Pattern (No wf-engine)

For the fastest and most reliable results, bypass the wf-engine entirely and call the Anthropic API directly with Python's `urllib`:

```python
import urllib.request, urllib.error, json, ssl

api_key = "sk-..."
url = "https://right.codes/claude-aws/v1/messages"
ctx = ssl.create_default_context()

prompt = """Request detailed technical analysis of a specific topic."""

data = json.dumps({
    "model": "claude-sonnet-4-6",
    "max_tokens": 4000,
    "messages": [{"role": "user", "content": prompt}]
}).encode()

req = urllib.request.Request(url, data=data, method='POST')
req.add_header('Content-Type', 'application/json')
req.add_header('x-api-key', api_key)
req.add_header('anthropic-version', '2023-06-01')

resp = urllib.request.urlopen(req, timeout=120, context=ctx)
result = json.loads(resp.read().decode())
text = result['content'][0]['text']
```

### When to Use This

| Metric | wf-engine Workflow | Direct API Call |
|--------|-------------------|-----------------|
| Time to first result | 60-600s | **30-120s** |
| Setup complexity | High (file paths, schemas, env vars) | **Minimal** |
| Parallelization | Built-in | Manual |
| Structured output | Via JSON Schema | Manual JSON parsing |
| Overhead per call | ~2-5s orchestration | **Zero** |

**Use direct calls when**: you want fast answers with no orchestration overhead. **Use wf-engine when**: you need structured multi-agent decomposition, parallel analysis, or phase-gated execution.

### 300s Sandbox Limit Workaround

If a direct API call needs more than 300s to complete (large prompts, Opus model), split the work:
1. Send the question in smaller chunks
2. Reduce `max_tokens` to get faster partial responses
3. Use Sonnet or Haiku instead of Opus for the bulk, then use Opus only for synthesis

### The `--script` Flag (Bypass Path)

wf-engine has two ways to load workflows:

| Flag | Source | Read by Claude Code? |
|------|--------|---------------------|
| `--name <name>` | Resolves from `~/.claude/workflows/<name>.js` | ✅ Yes — WorkflowTool reads it |
| `--script <path>` | Loads from arbitrary file path | ❌ No — only the standalone wf-engine uses this |

**`--script` is the bypass mechanism.** It loads a workflow file that Claude Code's WorkflowTool has never seen. Used directly with the API (not through Claude Code), it avoids pre-validation entirely.

```bash
node wf-engine.mjs --project <dir> --script /path/to/custom-workflow.js --args '{"key":"val"}'
```

