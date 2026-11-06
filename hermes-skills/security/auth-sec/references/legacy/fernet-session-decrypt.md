<!-- archived from /root/.hermes/skills/security/fernet-session-decrypt/SKILL.md on 2026-10-21 -->

---
name: fernet-session-decrypt
description: >-
 授权物资上 Fernet 加密的 Telethon/Pyrogram session_string（gAAAAA...）碰撞解密：
 从 .env / Vite@fs / 主机读盘收集 ENCRYPTION_KEY，解出可外连明文 session。
 用户提到 Fernet、ENCRYPTION_KEY、gAAAAA、session_string 密文、Sticker 解 session、
 缺密钥无法登录时使用。上游 tg-cloud-panel；挖钥可并行 vite-fs-read。
---

> 归档卡：原目录 `/root/.hermes/skills/security/fernet-session-decrypt`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/fernet-session-decrypt/…')`，不要相对 `references/legacy/` 解析。

# Fernet 会话解密（Cursor Skill）

## 何时用

- 面板导出 `session_string` 以 `gAAAAA` 开头
- 账号显示 LIVE 但外连失败
- 已拿到疑似 `.env` / 密钥候选

## 真源

1. `docs/playbooks/Fernet会话解密手法.md`
2. `tools/ops/fernet_session_decrypt.py`
3. 挖钥：`vite-fs-read` · WolfStack/Portainer exec · 主机 `.env`

## 强制步骤

1. 确认密文来自授权案卷物资。
2. 收集候选钥（`.env`、Vite `@fs`、容器文件）写入 keys 文件。
3. ```bash
 python3 tools/ops/fernet_session_decrypt.py selftest # 升级后先自检
 python3 tools/ops/fernet_session_decrypt.py decrypt \
 --token-file <json或文本> --keys-file <env或vite keys_from_fs.env> \
 --out exports/bot-recovery/<案卷>/接管/
 ```
4. 明文 session → Telethon/Pyrogram 验活；更新 STATUS（L2/L3）。入库走 `tg-account-library`。
5. 无 KEY 时并行 `vite-fs-read` / 主机面，**禁止**宣称已可登录。

## 成功口径

L1 密文确认 · L2 解密成功 · L3 外连验活。

## 不要做

- 把明文 session 写入可公开同步文档
- 无解密证据结案

## 批量解密工具

`tools/ops/fernet_batch_decrypt.py` — 批量 Fernet session 解密，支持从文件/stdin 批量输入 token。
