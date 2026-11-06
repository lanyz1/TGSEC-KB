# 同机双端口：TG 挖人 SPA + 群管 FastAPI（2026-09-20）

指纹：`IP:4000` Express + Vite SPA 标题「TG 挖人后台」；同 IP `:8080` uvicorn FastAPI 标题「登录 - 群管机器人后台」，OpenAPI/docs 常开。

## 立刻做

1. nmap 同 IP 常开 `4000`（Express）+ `8080`（uvicorn）；不要只打用户给的那一个端口。
2. `:8080/openapi.json` → 全路由表（广告/教师/欢迎语/开关…）；登录是 **form** `username`+`password` POST `/login`（JSON 会 422 missing）。
3. `:4000` 下主包（`/assets/index-*.js`）：
   - `baseURL:"/api"`
   - `localStorage` 键 **`tg_miner_token`** → `Authorization: Bearer ${token}`
   - 登录合约常是 **仅密码**：`Un.post("/login",{password:e})`（不是 username+password）
   - 业务面：`/accounts`、`/accounts/login/start|submit`、`/users`、`/dm/*`、`/stats`、`/dm-templates`、`/spy-accounts`…
4. SPA fallback：`/.env` `/.git/HEAD` 等回 **同长度 HTML**（~403B）= index，不是泄露；真 API 回 JSON `{"error":"未授权"}` / `{"error":"密码错误"}`。

## 弱口令

- 4000：只喷 `{password}` 到 `POST /api/login`；错密统一「密码错误」（无用户名字段）。
- 8080：form 喷；失败页带「用户名或密码错误」；用 cookie jar 跟进 `/switches` 判是否真登录（仅看 200 HTML 会误报——未登录也常 200 回登录壳或同长页）。
- **8080 OpenAPI 的 422 missing ≠ 未授权写**：很多路由先跑 Pydantic 再查 session；补全 form 字段后常直接 200 回登录 HTML。JSON Content-Type 更容易 422，真写要用 `application/x-www-form-urlencoded` / multipart（见 schema）。

## 登录卡死别死磕

密码/JWT/session forge 一轮无 HIT → **立刻**同 IP `:8888` 目录列表 + `/24` 横向（见 `subnet-lateral-when-login-stuck.md`）。用户会明确讨厌「只爆破」。

同 C 段常见旁车：License SaaS、TRX racing 面板、iM 远控、UFO 模拟器 —— 未授权面往往比主登录好打。

## 与 CASE

同类：`domains/CASE-INDEX.md` → api-security `711tock` / `tg-cloud-export-bola` / `715tg`。
开打顺序：`pentest-execution` → `tgsec-suite` → CASE → 本文件 → 抠包 → 双端口齐打 → 登录卡住则横向。

@TGSEC社区 · @TGSEC-Qtzuu 整理
