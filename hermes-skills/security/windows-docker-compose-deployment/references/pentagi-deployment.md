# PentAGI Deployment Reference

**Target**: https://github.com/vxcontrol/pentagi
**Repository size**: 147MB
**Stack**: Go backend + React/TypeScript frontend + PostgreSQL(pgvector) + Scraper
**Deployment**: Docker Compose (4 containers)

## Architecture

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `pentagi` | `vxcontrol/pentagi:latest` | `8443` (HTTPS) | Go REST+GraphQL API + React frontend |
| `pgvector` | `vxcontrol/pgvector:latest` | `5432` | PostgreSQL with pgvector extension |
| `pgexporter` | `quay.io/prometheuscommunity/postgres-exporter` | `9187` | DB metrics |
| `scraper` | `vxcontrol/scraper:latest` | `9443` | Web scraping service |

## LLM Provider Config

### DeepSeek (tested, working)

```bash
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_SERVER_URL=https://api.deepseek.com
# ⚠️ CRITICAL: DEEPSEEK_PROVIDER must be EMPTY, not "deepseek"
# If set to "deepseek", pentAGI prefixes model names as "deepseek/deepseek-v4-flash"
# which the DeepSeek API rejects with "supported model names are deepseek-v4-pro or deepseek-v4-flash"
DEEPSEEK_PROVIDER=

# Embedding also uses DeepSeek
EMBEDDING_URL=https://api.deepseek.com
EMBEDDING_KEY=sk-...
EMBEDDING_MODEL=deepseek-chat
EMBEDDING_PROVIDER=openai
```

### Provider Prefix Trap

The `ApplyModelPrefix` function in `backend/pkg/providers/provider/litellm.go` prepends `prefix + "/"` to every model name when the prefix is non-empty. For DeepSeek, setting `DEEPSEEK_PROVIDER=deepseek` causes all model names to become `deepseek/deepseek-v4-flash` etc., which the DeepSeek API does not support. **Always leave the provider prefix empty for direct API providers.**

## .env Minimum Config

```bash
# DeepSeek (MUST leave DEEPSEEK_PROVIDER empty)
DEEPSEEK_API_KEY=<your-key>
DEEPSEEK_SERVER_URL=https://api.deepseek.com
DEEPSEEK_PROVIDER=

# Security (generate random 32-char string)
COOKIE_SIGNING_SALT=<random-32-chars>

# Keep at defaults for local dev
PENTAGI_POSTGRES_PASSWORD=postgres
PUBLIC_URL=https://localhost:8443
CORS_ORIGINS=https://localhost:8443

# Free search (no API key)
DUCKDUCKGO_ENABLED=true
```

## Docker Compose Services

From `docker-compose.yml`:
- **pgvector**: Health check on port 5432, waits for healthy before pentagi starts
- **pentagi**: Depends on pgvector (healthy), runs goose migrations on startup, then starts API server
- **scraper**: Web scraping service, listens on port 443 inside container (mapped to 9443)
- **pgexporter**: Prometheus PostgreSQL exporter, metrics on 9187

## Startup Sequence

1. Networks + Volumes created
2. pgvector starts → waits for healthy status
3. scraper starts
4. pgexporter starts
5. pentagi starts (waits for pgvector healthy)
6. pentagi runs 26+ goose database migrations
7. API server starts on `:8443` with TLS

## .env Changes Require Container Rebuild

`docker compose restart` does NOT reload .env — the env vars are baked into the container at creation time.
After changing .env, you MUST recreate the container:

```bash
# Option A: force-recreate single service
docker compose up -d --force-recreate pentagi

# Option B: full teardown and rebuild (also recreates networks)
docker compose down
docker compose up -d
```

## Verification

```bash
# All containers running
docker compose ps

# Web UI reachable
curl -sk https://localhost:8443 | head -5
# Should return HTML with <title>PentAGI</title>

# Check migrations
docker compose logs pentagi | grep "migrated database"

# Check health
docker compose logs pentagi | grep "API server listening"

# Verify env var inside container
docker exec pentagi env | grep DEEPSEEK_PROVIDER
```

## Admin Account & API Access

The auto-seeded admin user `<EMAIL-REDACTED>` has a bcrypt password set during initial
migration. The raw password is unknown — reset it via direct SQL.

### Password Reset via SQL

**Critical: bcrypt hash prefix must be `$2a$`, NOT `$2b$`.**

Go's `golang.org/x/crypto/bcrypt` package uses the `$2a$` prefix. Python's
`bcrypt` library generates `$2b$` by default, which Go rejects as invalid.
Generate the hash with `$2a$` prefix:

```python
import bcrypt
hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt(rounds=10))
hashed_2a = hashed.decode().replace("$2b$", "$2a$")
```

Then write the SQL to a file to avoid shell `$` variable interpolation:

```sql
-- save as reset_pwd.sql
UPDATE users SET password='$2a$10$...' WHERE id=1;
```

Apply via:
```bash
cat reset_pwd.sql | docker exec -i pgvector psql -U postgres -d pentagidb
```

### Login via API (session-based)

pentAGI uses **session cookies**, not bearer tokens. Use a cookie jar:

```python
import http.cookiejar, urllib.request, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ctx),
    urllib.request.HTTPCookieProcessor(cj)
)
# Login
opener.open(urllib.request.Request(
    "https://localhost:8443/api/v1/auth/login",
    data=json.dumps({"mail": "<EMAIL-REDACTED>", "password": "admin123"}).encode(),
    headers={"Content-Type": "application/json"}
))
# Subsequent requests auto-send the session cookie
```

Where `auth` cookie looks like:
```
auth=MTcyNjg3Njg5OHxOd3dBTkZwRlFUMUJSVFo1UlRWWlRUVkZQVHc9PXw0Njc5Zjk3OTYxZmEzZWQ4NWM3ZDBkZTgxMjRkOWU3MDg5M2UzOTRlY2FjZjY3NmYzOTNkMzc3OGVlNzIzZjQ1
```

## Creating a Penetration Test Flow (via GraphQL)

### 1. Create the LLM Provider

pentAGI require a provider record in the database before flows can run.
Create via GraphQL mutation:

```graphql
mutation {
  createProvider(
    name: "DeepSeek",
    type: deepseek,
    agents: {
      simple: { model: "deepseek-v4-flash" },
      simpleJson: { model: "deepseek-v4-flash" },
      primaryAgent: { model: "deepseek-v4-pro" },
      assistant: { model: "deepseek-v4-pro" },
      generator: { model: "deepseek-v4-pro" },
      refiner: { model: "deepseek-v4-pro" },
      adviser: { model: "deepseek-v4-pro" },
      reflector: { model: "deepseek-v4-flash" },
      searcher: { model: "deepseek-v4-flash" },
      enricher: { model: "deepseek-v4-flash" },
      coder: { model: "deepseek-v4-pro" },
      installer: { model: "deepseek-v4-flash" },
      pentester: { model: "deepseek-v4-pro" }
    }
  ) { id name type }
}
```

**Model naming**: Use bare model names (e.g. `deepseek-v4-flash`), NOT
`provider/model` format. The backend prefixes internally only when
`DEEPSEEK_PROVIDER` is set.

### 2. Create a Flow

```graphql
mutation {
  createFlow(
    modelProvider: "deepseek",
    input: "Target: <url>. Perform penetration testing: DNS recon, port scan, web fingerprint, dir busting, SQLi, XSS, SSRF, auth bypass, API discovery. Report all findings."
  ) { id title status }
}
```

The `input` field is a free-form text prompt that instructs the pentesting agents.
pentAGI parses this and spawns Researcher → Developer → Executor agents.

### 3. Flow Execution

Once created, pentAGI automatically:
1. Downloads the Kali Linux image (`vxcontrol/kali-linux`) for the sandboxed terminal
2. Spawns a primary terminal container
3. Runs multi-agent pentesting pipeline
4. Streams results via GraphQL subscriptions

Monitor via:
```bash
# Flow status
docker exec pgvector psql -U postgres -d pentagidb -c "SELECT id, title, status FROM flows ORDER BY id DESC LIMIT 5;"

# Live logs
docker compose logs -f pentagi
```

## First-Run Notes

- Image pull size: ~1.5-2GB total (pgvector ~500MB, scraper ~550MB, pentagi built from Dockerfile ~200MB, postgres-exporter ~35MB)
- Image pull + build time: 10-20 minutes on first run depending on connection speed
- Kali Linux pentesting image pulled on-demand when first flow runs (~additional 1-2GB)
- Database migrations run on every container start
- Self-signed TLS cert generated at first startup (accept browser warning)
- Register first user at `https://localhost:8443` in browser (or reset via SQL as above)

## Known Issues

- **Docker Desktop + WSL2 first boot**: After fresh WSL install, a reboot is mandatory before Docker Desktop can use the WSL2 backend
- **DEEPSEEK_PROVIDER trap**: Must be empty, not `deepseek` — causes model name prefix corruption
- **bcrypt prefix mismatch**: Python `$2b$` vs Go `$2a$` — always replace `$2b$` with `$2a$` when resetting passwords via SQL
- **docker compose restart doesn't reload .env**: Must use `--force-recreate` or full down+up
- **DNS resolution failures**: `dl.reclaude.ai` no longer resolves (ReClaude's update server is down)
- **Device revocation**: ReClaude's `device_revoked` (401) means the device was deauthorized server-side — need to re-login via `reclaude login`

## Docker Hub China Network Issues

When deploying pentAGI from a China-based network, Docker Hub is frequently blocked or severely throttled.

### Registry Mirrors

Add to `C:\ProgramData\Docker\config\daemon.json`:
```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me",
    "https://hub.rat.dev",
    "https://docker.m.daocloud.io",
    "https://dockerhub.timeweb.cloud"
  ]
}
```
Then restart Docker Desktop.

### Kali Linux Image Workaround

The `vxcontrol/kali-linux` image often cannot be pulled from China. Workaround:

```bash
docker pull kalilinux/kali-rolling:latest
docker tag kalilinux/kali-rolling:latest vxcontrol/kali-linux:latest
```

Also set in `.env`:
```bash
DOCKER_DEFAULT_IMAGE_FOR_PENTEST=vxcontrol/kali-linux
```

### Proxy for DuckDuckGo / Search

pentAGI's DuckDuckGo search tool is often rate-limited (HTTP 202) from Chinese IPs. If a local proxy is available (e.g. `127.0.0.1:10808`):

1. Add to `docker-compose.yml` pentagi service environment block:
```yaml
- HTTP_PROXY=${HTTP_PROXY:-}
- HTTPS_PROXY=${HTTPS_PROXY:-}
- NO_PROXY=${NO_PROXY:-}
```

2. Set in `.env`:
```bash
PROXY_URL=http://127.0.0.1:10808
HTTP_PROXY=http://127.0.0.1:10808
HTTPS_PROXY=http://127.0.0.1:10808
NO_PROXY=localhost,127.0.0.1,api.deepseek.com,.deepseek.com
```

3. Recreate container: `docker compose up -d --force-recreate pentagi`

**Without a working search engine**, Agent flows stall on the recon phase (all DuckDuckGo calls return 202). Either proxy the searches or configure a non-DuckDuckGo search provider (Tavily, Google API, SearXNG).

### Embedding Model Issues

DeepSeek's `deepseek-chat` model does not support embeddings. Setting `EMBEDDING_PROVIDER=openai` with DeepSeek's URL causes 404 errors when the Agent tries to store results in vector memory. This is non-fatal (agents still work, they just can't persist knowledge), but resolves when using a proper embedding provider.

## Flow Execution Monitoring

### Check if Flow is making progress

```bash
# Agent execution logs
docker exec pgvector psql -U postgres -d pentagidb -c "SELECT initiator, executor, left(task,60) FROM agentlogs WHERE flow_id=<ID> ORDER BY id;"

# Tool calls
docker exec pgvector psql -U postgres -d pentagidb -c "SELECT name, status, left(result,80) FROM toolcalls WHERE flow_id=<ID> ORDER BY id DESC LIMIT 10;"

# Tasks
docker exec pgvector psql -U postgres -d pentagidb -c "SELECT id, status, title FROM tasks WHERE flow_id=<ID>;"

# Terminal container
docker ps -a --filter name=pentagi-terminal-<ID>
```

### Flow Stuck on DuckDuckGo

All DuckDuckGo calls returning `unexpected status code: 202` = rate limited. No search results = agents can't plan. Fix: configure proxy or alternative search engine, delete stuck flow, recreate.

### Clean up stuck flows

```sql
DELETE FROM flows;  -- removes all flows, agents restart cleanly next createFlow
```

### Agent types and their roles

| Agent Type | Role |
|-----------|------|
| `memorist` | Searches long-term memory for prior work |
| `searcher` | Web/DuckDuckGo search |
| `generator` | Plans attack methodology |
| `primary_agent` | Main orchestrator |
| `pentester` | Executes exploitation in Kali container |
