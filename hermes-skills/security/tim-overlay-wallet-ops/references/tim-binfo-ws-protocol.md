# TIM binfo WebSocket client protocol

Use when platform REST admin is closed (`90009`) but you hold a normal user login `token` (userSig) + `accid` + `imAppid`.

## Connect

```
wss://wsssgp.im.qcloud.com/binfo?sdkappid=<SDKAppID>&instanceid=<16hex>&random=<float>&platform=7&host=unknown&version=-1&sdkversion=2.27.6&compress=gzip
```

Headers: `Origin: https://web.sdk.qcloud.com`, normal browser UA. Handshake timeout ~15s.

## Frame codec

- **Outbound:** pack the JSON string as binary by writing each `charCodeAt(i) & 0xff` into a Buffer (latin1). No 2/4-byte length prefix.
- **Inbound:** try `JSON.parse(utf8)` first; some pushes use a `COMP` magic + compressed body — if parse fails, strip magic and inflate.

## Head template

```json
{
  "ver": "v4",
  "platform": 7,
  "websdkappid": 537048168,
  "websdkversion": "1.7.3",
  "sdkappid": <SDKAppID>,
  "contenttype": "json",
  "reqtime": <unix_s>,
  "sdkability": 192371,
  "tjgID": "",
  "seq": <inc>,
  "servcmd": "<cmd>"
}
```

Pre-login add `identifier` + `usersig`. Post-login add `a2` + `tinyid` + `status_instid` from login body **`A2Key` / `TinyId` / `InstId`** (PascalCase — lowercase-only reads miss a successful login). Dual-head (a2 + identifier/usersig) is a valid probe when a2-only fails a specific cmd.

Envelope: `{ "head": <head>, "body": <body> }`.

## Login

- cmd: `im_open_status.wslogin`
- body: `{ "state": "Online", "isWebUniapp": 0, "InstType": 0 }`
- success: `head.retcode === 0` / body `ErrorCode:0` **and** extract `A2Key`/`TinyId`/`InstId`. Heartbeat: `im_open_status.hello` about every 25–60s with the post-login head.

Failure codes match REST userSig table (`70001` kicked, `70009` secret, `70013` id mismatch).

## Messaging

### REST vs WS authority split

| Path | Who | Notes |
|---|---|---|
| REST `openim/sendmsg`, admin roam | TIM **admin** | Member/userSig → `90009` even for friends |
| WS `openim.sendmsg` after wslogin | Member | Real client C2C |
| REST/WS `group_open_http_svc.send_group_msg` | Group member | Works without TIM admin |
| REST/WS `destroy_group` | **Owner only** | Admin role / WS login still `10007` |
| REST `sns/friend_add` to hot owners | Often blocked | `38001` 禁止违规加好友 — stop |

### AES text (required for CJK)

```js
const key = Buffer.alloc(16, 0);
Buffer.from('666888').copy(key);
const c = crypto.createCipheriv('aes-128-ecb', key, null);
c.setAutoPadding(true);
const b64 = Buffer.concat([c.update(Buffer.from(text, 'utf8')), c.final()]).toString('base64');
```

Decrypt mirror with `createDecipheriv`. Put `b64` in `MsgContent.Text`.

### C2C

cmd `openim.sendmsg`:

```json
{
  "From_Account": "<accid>",
  "To_Account": "<peer>",
  "MsgRandom": <int>,
  "MsgBody": [{ "MsgType": "TIMTextElem", "MsgContent": { "Text": "<aes-b64 or ascii>" } }]
}
```

`ErrorCode:0` = accepted. `90003` = account field invalid (usually wrong case/shape).

### Group

cmd `group_open_http_svc.send_group_msg`:

```json
{
  "GroupId": "<tid>",
  "Random": <int>,
  "MsgBody": [{ "MsgType": "TIMTextElem", "MsgContent": { "Text": "..." } }]
}
```

### Reads

- `group_open_http_svc.get_joined_group_list` `{Member_Account, Limit, Offset, ResponseFilter:{GroupBaseInfoFilter:[Type,Name,Owner_Account,MemberNum], SelfInfoFilter:[Role]}}`
- `group_open_http_svc.get_group_member_info` `{GroupId, Limit, Offset, MemberInfoFilter:[Role,JoinTime,NameCard]}`
- `group_open_http_svc.get_groups_info` may answer `10003` for non-members even with a filter — prefer joined list + member info when inside
- Roam: field names are picky (`Peer_Account`, `LastMsgTime`, …). Prefer live push listen over broken roam shapes

### Owner

- `group_open_http_svc.destroy_group` `{GroupId}` → owner `ErrorCode:0`, else `10007`
- `group_open_http_svc.change_group_owner` `{GroupId, NewOwner_Account}` — target must already be a member
- `group_open_http_svc.apply_join_group` `{GroupId, ApplyMessage}` → `WaitAdminApproval` / `forbidden to apply` / `10010`

## Push handling

`im_open_push.msg_push` / new_msg events carry `C2cMsgArray` / `GroupMsgArray`. Decrypt `Text` with the same AES key. Filter `From_Account === self` as sync echoes when scoring replies.

## Minimal Node skeleton order

1. WS open → wslogin
2. On OK stash a2/tiny/inst
3. get_joined_group_list
4. Optional AES C2C / group send
5. Listen until timeout; hello on interval
6. destroy only groups where SelfInfo.Role is Owner
