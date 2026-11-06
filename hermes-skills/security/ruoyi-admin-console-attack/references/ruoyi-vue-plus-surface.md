# RuoYi-Vue-Plus admin surface — observed shapes

Concrete endpoint and message shapes for the admin gateway. Use these to skip the enumeration
phase; verify each against the target's own `/v2/api-docs` before relying on it.

## Module discovery

```
GET <gateway>/swagger-resources
-> [{"name":"wuquan-auth","url":"/auth/v2/api-docs"},
    {"name":"wuquan-system","url":"/system/v2/api-docs"},
    {"name":"wuquan-app","url":"/wuquan/v2/api-docs"},
    {"name":"team-system","url":"/team-system/v2/api-docs"},
    {"name":"hosting-server","url":"/hosting/v2/api-docs"}, ...]
```

Each doc: `swagger: "2.0"`, `basePath` = the module's own prefix, `host` = the **internal**
backend address (leaks the private topology), `definitions` = full request bodies.
`securityDefinitions.Authorization` is `{type: apiKey, name: Authorization, in: header}`.

A module doc can exist at `/v2/api-docs` under one base and 404 under another (the auth module is
often not exposed). Probe `/<module>/v2/api-docs` for each name from `swagger-resources`; do not
assume the doc set is complete or uniform.

## The three response strings that tell you the auth state

| String | Meaning |
|---|---|
| `令牌不能为空` | no token reached the filter — route is live, auth is enforced |
| `access deny` | token WAS parsed and is correctly signed, but rejected at the app's scope/permission layer |
| `登录状态已过期` / `令牌已过期或验证不正确` | session replaced, or the signature/claims failed |

`access deny` on one path and success on another, for the SAME token, is the signature of an
application authorization check. It is not a signature problem and not a path problem.

## Login oracle strings

```
unknown user          -> {"msg":"Login user:<x> doesn't exist."}
wrong password        -> {"msg":"Wrong user name or password"}
password OK, MFA gate -> {"msg":"请输入验证码"}          # the hit
wrong MFA code        -> {"msg":"验证码错误"}
no MFA field sent     -> {"msg":"请输入验证码"}
missing username      -> {"msg":"用户/密码必须填写"}
```

The login body is `{username, password}` plus the MFA field, which forks name `googleCode`
(Google Authenticator TOTP) rather than `code`/`captcha`.

Sibling module logins answer with a different, per-module user table:
`/hosting/login` -> `登录用户不存在`; `/team-system/login` -> `登录管理员不存在或已删除`.
Empty username -> `用户名不能为空`. Those are separate account stores from `/auth/login`.

## Settlement/session claims in the JWT

Base (customer app): `{user_id, user_key, username}` — `user_key` is a UUID used as the session
lookup key.

Admin gateway tokens add fork claims:
`{user_id, login_type: "login_user", user_key, login_scope: "manager", username}`.

`login_scope` is set by the issuing endpoint, not by the request. Confirmed ineffective overrides:
body `scope` / `loginScope` / `type` / `loginType` / `clientId` / `tenantId` / `grantType` /
`userType` / `deviceType`; headers `clientid` / `Clientid` / `Client-Id` / `Login-Scope`
interpolation. One probe each, then stop.

## Admin CRUD naming pattern

Generated RuoYi controllers expose an entity as a set of sibling routes. Given entity `<e>`:

```
GET    <base>/<e>/list          GET  <base>/<e>/{id}
POST   <base>/<e>               PUT  <base>/<e>
DELETE <base>/<e>/{ids}         POST <base>/<e>/export
POST   <base>/<e>/importData    POST <base>/<e>/importTemplate
POST   <base>/<e>/changeStatus  DELETE <base>/<e>/refreshCache
```

Entity names are lowercase-camel and often prefixed (`iImgroupinfo`, `imappidconfig`,
`acctrealname`, `reportreason`). Sweep these by using the documented names from the SWAGGER (the
list above is the *shape*, not the wordlist). Enumerate an entity from its doc, not from a guessed
verb list.

Destructive siblings often sit next to list on the same controller. Example shape for IM group
admin destroy (verify field names from `definitions`, do not invent):

```
POST <base>/iImgroupinfo/destroyTeam
body ImGroupInfo-like { tid, imAppid, owner, serverId, ... }
```

Oracle ladder on that class of path: no token → `令牌不能为空`; wrong principal → cast error
(`LoginUser` vs `ImLoginUser`); signed under-scoped manager token → `access deny`; only a
CRUD-capable admin principal + re-read proves remove. Customer/app JWTs denying destroy does **not**
contradict TIM owner `destroy_group` working — different principal (see
`references/destroy-authority-matrix.md`).

## The `type` / `value` setting pattern

Several unrelated controllers expose a generic two-field setter. The body is `{<subject>, type,
value}` and the type domain differs per controller — probe the type alphabetically and read the
validation error, which names the domain (`请选择要修改的扩展类型`, `请输入类型`, `请输入值`).

- `type` can be an INT enum on one endpoint and a string field-name on another. A
  `Cannot deserialize value of type int from String` error tells you which.
- The subject field is the resource id (`tid`, `groupId`, `channelId`).

Observed on one fork's group setter (`teamApi/customerSetting`, body `{tid, type, value}`):

```
own group,  type=1   -> 隐私模式值输入错误      (type IS valid, value rejected)
own group,  type=2   -> 设置成功
own group,  type=3   -> 禁止撤回值输入错误      (type IS valid)
own group,  type=11  -> 设置成功
own group,  type=4..10 -> 类型不存在！          (sparse: a hole, not a sequence)
own group,  type=zzzz  -> 类型不存在！
someone else's group, EVERY type incl. zzzz -> 权限不足，修改失败！
```

The last line is the important one: the ownership gate fires before the type is read, so a victim
subject tells you nothing about the domain. Make a throwaway resource (`teamApi/createTeam` ->
`{"data":{"tid":"<new>"}}`) and enumerate against that.

## Shared-secret (`apiKey`) helper APIs

A `managerApi`-style controller exposes cross-resource operations that the customer app never
calls: add/batch-invite members, modify official accounts, query/renew/update team info, update
users. Body shape is a flat object carrying `{apiKey, appid, serverId, ...}` plus per-operation
fields.

- These controllers frequently skip the token check entirely and validate PARAMETERS FIRST, so an
anonymous request that returns `请输入APPID` / `请输入群等级` proves the route is reachable with no
session.
- The `apiKey` check runs AFTER parameter validation, so parameter errors say nothing about the
key. Once parameters are complete the answer collapses to a single permission string for every
wrong key — that is the oracle, and it makes the key a credential hunt, not a guessing game.
- Platform names, imAppids, clientids, domain words and known dump secrets do not satisfy it.

### Public partner SaaS holding the same key

A secondary port on the platform's own origin IP can host a *public* white-label API that proxies
the same helper calls with a key you do not have. Fingerprints: FastAPI-shaped errors
(`{"detail": "..."}`), `GET /health` -> `{"ok":true,"service":"public"}`, an inline-JS docs page
plus a lookup portal. Endpoints seen:

```
POST /api/add-friend     headers {fromUserSig, authorize}  body {cardKey, serverId, fromAccid, toAccid}
                         -> {"success":false,"message":"fromUserSig无效"}   (userSig checked BEFORE authorize)
POST /api/card-history   body {cardKey, page, pageSize}
                         -> {"detail":"卡密无效"}  for an unknown card; returns bindings/remaining/expiry on a hit
```

The service holds the platform `apiKey` internally, so it is both a capability map for the gated
controller and a source of fresh oracles (its `authorize` developer key, its card-key space). Other
paths on that service answer with the WAF page rather than 404 — sweep it, but expect only a couple
of live routes.

## Registration / card-secret gates

Two independent registration surfaces, both commonly gated:

- system: `/auth/register` -> `当前系统没有开启注册功能！` (disabled), `/system/user/register`
  requires a token.
- hosting/agent: `/hosting/hostingUser/register` and `/team-system/end-user/register` require a
  `cardSecret` field. Invalid values return a single uniform string (`卡密无效，请核对后重试`) with
  **no length or format oracle** — do not attempt to brute-force it.

## Shard (server) scoping

App APIs carry a `serverId` dimension taken from the session, not the request body. A token from
one shard resolves only that shard's resources:

```
teamApi/customerSetting {tid:<other shard's tid>}          -> 群组不存在！
reportApi/submitReport  {targetGroupId:<other shard tid>}  -> 被举报群组不存在或不属于当前服务
```

A body `serverId` parameter does not switch the context, and `login_scope`-style headers do not
either. Read the shard out of the login response (`imAppid`) and treat it as part of the authz
scope: "not found" here means "wrong shard", not "resource absent".

## Internal-only paths

`/inner/uq/im-group/*` and `/inner/uq/im-user/*` (list, memberList, getGroupInfo,
query-owner-group-list, set-mute-all-status, batch-add-member, send-message) appear in the public
doc set but are filtered at the edge on every ingress tested. Treat as out of reach unless an
origin/alternate-ingress split (see `waf-evasion-and-credential-attack` §6) proves otherwise.

## Cast-error leakage

Calling a controller with a token of the wrong principal type leaks the internal class names:

```
class com.<vendor>.system.api.model.LoginUser cannot be cast to
class com.<vendor>.system.api.domain.ImLoginUser
```

This is a free, reliable oracle: it proves (a) your token authenticated, (b) the controller is
reachable, and (c) the module expects a different principal (here: an app/platform user rather
than a sys/admin user). Use it to decide which token class an endpoint needs before hunting for
one.
