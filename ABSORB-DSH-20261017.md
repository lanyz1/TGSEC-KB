# DSH 吸收记录 · TGSEC-Qtzuu (2026-10-17)

## 来源

- 上游仓库：https://github.com/lanyz1/TGSEC-Qtzuu （master，commit b401bbe1，2026-10-12）
- 本地克隆：`C:\Users\Administrator\Desktop\1\TGSEC-Qtzuu`
- 知识库根（本文件所在目录）：`C:\Users\Administrator\.dsh\tgsec-kb`
- 技能根：`C:\Users\Administrator\.dsh\skills`（DSH 官方 `<id>/SKILL.md` 布局）

## 已吸收技能（30）

- `0day-exploit-library`
- `about-security`
- `black-cat-redteam`
- `cdn-origin-tracing`
- `claude-bughunter`
- `gambling-platform-pentest`
- `ghost-cms-content-api-sqli`
- `gitea-docker-webauth-bypass`
- `givewp-php-object-injection-rce`
- `hack-skills`
- `handlebars-ast-injection-rce`
- `http2-cookie-bomb-dos`
- `keycloak-reset-flow-bypass`
- `lfi-rfi-exploit`
- `lobechat-ssrf-redirect`
- `mathjs-sandbox-escape-rce`
- `metabase-preauth-sqli`
- `n8n-form-trigger-rce`
- `open-redirect-chain`
- `orm-json-key-sqli`
- `pentest-execution`
- `pentest-redteam`
- `pfsense-xss-to-rce`
- `reverse-skill`
- `secatlas`
- `security-kb-ingest`
- `simple-git-config-rce`
- `stopen`
- `tgsec-suite`
- `web-sec`

## 路由

- 关键词表：`ROUTING.md` ｜ 主题表：`MASTER.md` ｜ 首步：`AGENTS.md` ｜ 小白入口：`START.md`
- 实战课总表：`domains/CASE-INDEX.md`
- 域索引：`domains/<面>/README.md`，顺序 README → case-lessons → playbook-6000 → hunter-6000 → src-methods

## 已知缺口

- 7 个 LFS 大件在服务端 404（`domains/0day-exploits/ios-vphone/vphone-aio/vphone-cli.tar.zst.part_a*`，2GB 级），其余 27000+ 文件完整。
- Windows 长路径需 `core.longpaths=true`，克隆仓已设置。
