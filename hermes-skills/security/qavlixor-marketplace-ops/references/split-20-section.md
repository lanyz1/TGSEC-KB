## 红线(硬性)
- 生产部署 202.95.1.135:**每次当次点名授权**,上一次授权不延续;绝不 push。
- 完成一个单元自动 git commit(不逐次问),但 **C 阶段逐页用户确认制** — 用户确认页面 OK 后才 commit + ops-log。
- 每次改动写 `docs/ops-log/YYYY-MM-DD-操作日志.md`(一天一文件,同天追加;规范见 ops-log/README.md)。
- 禁读/回显密钥(`~/.claude/settings.json` 的 ANTHROPIC_AUTH_TOKEN 等)、禁凭证/token 入 memory、禁碰真实账号(<EMAIL-REDACTED>)、禁改测试账号密码。
- 演示账号(<EMAIL-REDACTED> / Global@2026、<EMAIL-REDACTED> / Demo@2026view)可给用户本地测试,但**不入 memory**。
- 中文回复。

