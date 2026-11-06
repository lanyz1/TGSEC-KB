# Public-repo credential candidate mining — case notes (2026-10)

Authorized case `hutaocards_20261017` (Saturney). Public operator repos only.

## What worked
- Cloned `g2nnyS_Postsort`, `g2nnyS_Postsort_Web`, `g2nnyS_LazyLive`, `erdongzou_Xboard`, `Saturney-Limited-*`.
- `grep -Ri` on `Postsort/config.yml` found default DB creds `postsort:postsort` (PostgreSQL/MySQL, database `postsort`). The earlier case-sensitive grep missed it.
- `git log -p --all -G 'APP_KEY|DB_PASSWORD|REDIS_PASSWORD|MAIL_PASSWORD|SECRET_KEY'` in `erdongzou_Xboard` surfaced a real-format `APP_KEY=base64:...` in history.
- `Postsort_Web/.env` exists in the repo; keys readable, values redacted.
- `LazyLive/chat.html` leaked operator personal domains: `s1.imlazy.ink:233`, `xypigeon.ink`, `lazy.ink`.

## What did not work
- Xboard `.env.example` `APP_KEY` is a **demo** key, not the live panel key; `secure_path` derived from it does not match.
- `postsort:postsort` did **not** authenticate on the live `114.132.243.207` MySQL/PostgreSQL.
- `files.xypigeon.ink` / `live.xypigeon.ink` DNS gone; `api.imlazy.ink` is ShizukuAPI; `s1.imlazy.ink` is Tengine live — personal-domain line closed.

## Lesson
Repo mining yields **candidate** credentials, not live access. Classify every candidate:
1. demo/placeholder (`.env.example`, docs, tests),
2. real-format default (`config.yml`, `docker-compose.yml`),
3. actual secret (history, committed `.env`).
Then test 1-2 times against the exact service, and close the line if rejected.
