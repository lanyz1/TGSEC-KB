# Scope gate and mis-sent targets

## Target relation

- In scope: the named target plus a host with the same A-record IP or a stack
  the target's homepage actually loads or iframes (real JS/iframe connection).
- Not enough: a shared app-distribution bucket, a sister brand, a FAQ/download
  page, a friend link, a sitemap entry, or a third-party IM widget.
- A shared bucket can contain the target app and a sister app. The target app
  is in scope; the sister app is not unless it independently meets the
  same-IP/JS test. Do not attack the sister to "find a weaker entry".

## Mis-sent target

- If the user sends a URL plus credentials and then immediately says
  "搞错了 / 发错了 / 继续任务", treat the new target as mis-sent.
- Do not scan it, do not log in, do not reuse the credentials, and do not keep
  the target in the report. Continue the original engagement.
- The user may have sent a real but unrelated target by mistake; acting on it is
  an out-of-scope event even if the credentials work.

## Reporting language

- Say what is in scope and what was deliberately not touched. This prevents a
  future agent from treating an untouched sister app as an unfinished surface.
- When a target is excluded, note the reason (no same-IP/JS relation), not just
  "not tested".
