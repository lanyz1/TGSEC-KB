## 支持文件

| 文件 | 内容 |
|---|---|
| `scripts/admin_cred_hunter.py` | 凭据来源清道夫(154 路径 + JS 挖密 + 差分登录探测 + 锁定保护) |
| `scripts/vuln_admin_site.py` | 回归靶场(含 SPA 兜底 / 锁定两种模式) |
| `references/2026-admin-auth-bypass-cve-map.md` | 2026 在野认证绕过 CVE 速查表(含 CVSS/版本/利用链/来源) |
| `references/credential-source-matrix.md` | 14 类凭据产地 × 精确路径 × 实测命令 × 拿到后怎么用 |
| `references/session-token-replay-from-db-backup.md` | **会话 token 直接复用**:用户表里的 `token` 列(无 TTL/无绑定/改密不失效)→ 从备份库/Parquet 取出即后台直登;含"已修复"逐入口复测矩阵、菜单口路由取证、legacy 库弱口令≠现网账号、客户端硬编码签名盐复算 |
| `references/bypass-matrix-path-method-header.md` | 401/403 路径·动词·头 全矩阵 + 限流绕过 |
