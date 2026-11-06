## WORDLISTS (Installed in ~/wordlists/)

```
common.txt         # Common directories and files
params.txt         # Parameter names (id, user_id, file, etc.)
api-endpoints.txt  # API endpoint paths (/api/v1/users, etc.)
dirs.txt           # Directory names
sensitive.txt      # Sensitive paths (.env, config.json, backup, etc.)
```

### Built-in Paths Worth Fuzzing

```bash
# Sensitive files
/.env
/.git/config
/config.json
/credentials.json
/backup.sql
/dump.sql
/.DS_Store
/robots.txt
/sitemap.xml
/.well-known/security.txt

# Admin panels
/admin
/admin/login
/administrator
/wp-admin
/manager
/console
/dashboard
/panel

# API discovery
/api
/api/v1
/api/v2
/graphql
/graphiql
/swagger
/swagger-ui.html
/api-docs
/openapi.json
/v1
/v2
```

---

