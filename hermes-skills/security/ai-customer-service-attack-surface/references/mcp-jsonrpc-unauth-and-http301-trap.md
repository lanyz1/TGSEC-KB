# MCP 服务注册与发现类平台 —— 未授权读写 + HTTP 301 方法降级陷阱

适用:目标出现 `/openapi.json` title 含 `MCP Server with Registration & Discovery`、`/mcp`、`/tools`、`/copilot/*`、`/ciam/*`、`register_service`/`import_catalog` 等工具名时。

## 0. 先解决入口(最贵的坑,先踩)

**现象**:`http://<host>/<path>` 的 POST 一律返回 `405 Method Not Allowed`,而响应头 `Allow: POST` —— **自相矛盾**。

**成因**:nginx 把 `:80` 上所有 POST **301** 到 `https://<host>:443/<同一路径>`。客户端(urllib/requests 等)跟随 301 时按 RFC 7231 把 **POST 降级为 GET**,应用的 GET 处理器于是正确地返回 `405 Allow: POST`。

**证据获取法**(勿靠猜):
```python
# 禁自动重定向的 opener, 抓原始 301 与 Location
class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
op = urllib.request.build_opener(NoRedir)
# POST 到 :80 -> 看 Location 头; OPTIONS/PUT 因不被降级会原样暴露 301
```

**铁律**:
1. 见到「405 但 Allow 含自己用的方法」⇒ **先查 301/302 方法降级**,再谈封禁/加固。
2. `:8443` 之类的备用端口可能只是**前端 SPA vhost**(未知路由回 `index.html` 兜底,已知路由才回真 JSON)—— 用「除 `/api/config`、`/health` 外是否全返 HTML」来判定,别把它当 API。
3. API 常在 `https://<host>:443`,且 Host/SNI 必须用**真域名**(ALB 多 IP,IP 直连可能走错 vhost)。

## 1. /mcp JSON-RPC 是独立攻击面(常整条无鉴权)

```bash
curl -sk -X POST https://<host>/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
curl -sk -X POST https://<host>/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
curl -sk -X POST https://<host>/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_server_health","arguments":{}}}'
```
`initialize`/`tools/list` 返 200 ⇒ 只是**存在性**,**不足以定级**。商务路由(`/copilot/*`、`/about`)挂 Bearer 而 `/mcp` 不挂,是本类目标的典型形态(原因:业务路由有 auth 依赖注入,协议入口没有)。

## 2. 未授权【写】定性法:空参调用(零状态变更)

对每个写工具发 `arguments: {}`:

| 响应 | 判读 |
|---|---|
| `-32000 Argument error: ... missing N required positional arguments: 'a','b'` | **handler 已执行、鉴权不存在** ⇒ 未授权可写;同时白送参数名 |
| `401`/`403` | 有鉴权,此路不通 |

错误信息即契约 ⇒ **永不猜参数名**。典型参数:
```
register_service(service_name, service_type, version, endpoints, capabilities)
register_capability(name, version, description, category)
import_catalog(catalog_data)
update_subcatalog(master_catalog_id, subcatalog_key, subcatalog_data)
delete_subcatalog(master_catalog_id, subcatalog_key)
delete_catalog(catalog_id)
deregister_service(service_id)
send_heartbeat(service_id, health_status, instance_id)
```

**影响升级链**:`register_service` 的 `endpoints` 可控 ⇒ 平台 orchestrator(常见 `http://localhost:8010`)会去调用 ⇒ **内网 SSRF / 供应链投毒**;`import_catalog`/`update_subcatalog` ⇒ 目录投毒;`delete_*` ⇒ 破坏性删除;`send_heartbeat` ⇒ **任意方为任意服务保活/伪造健康**。

## 3. 写验证的可逆性铁律(动手前先查删除动词)

- `register_service` ↔ `deregister_service` **存在** ⇒ 可做可逆验证。
- `register_capability` **无对应删除工具** ⇒ **绝不写**(留无法清除的残留)。
- 写入时的自保:把 `endpoints` 指向**本机丢弃端口**(如 `http://127.0.0.1:9/`)、`capabilities: []` ⇒ 平台永不选中、零对外请求。
- `deregister_service` 常是**幂等软标记**:多次调用只回 `Service marked as DEREGISTERING`(30s drain),**不硬删** ⇒ 必然留残留,**报告必须披露**(写明 `service_id`,请运维入库删)。

## 4. 同族必查:健康检查端点回显 bootstrap 配置

`GET /ciam/health`(或 `/health`、`/bootstrap`)可能未授权 200 回显 `bootstrap.config`: **IdP 池 ID + app client_id + client_secret + 管理员邮箱 + 环境号**。

**凭据有效性必须差分确证,不能凭单点下结论**(IdP 常开 `PreventUserExistenceErrors`,使「口令错」与「用户不存在」同码):

| 组 | 构造 | 期望 |
|---|---|---|
| D1 | 不带 SECRET_HASH | 报「configured with secret but SECRET_HASH was not received」 |
| D2 | 伪造 ClientId | `ResourceNotFoundException` ← **基线** |
| D3 | **正确 secret** | 推进到**业务规则层**(如 `SignUp is not permitted`)⇒ 校验通过 |
| D4 | **损坏 secret** | `Unable to verify secret hash` ⇒ 校验失败 |

D3/D4 错误不同 ⇒ 凭据为真。**但别急着等价成平台接管**:`/ciam/auth/api-token` 之类的端点可能要的是**用户级** `pool_name`+`access_key`+`secret_key` 三元组(client 凭据喂进去会回 `401 Invalid username or password`)⇒ 影响停在 IdP 层(可驱动 `InitiateAuth`/`ForgotPassword`)。

**不做的动作(零真实影响纪律)**:不爆破口令(Cognito 5 次失败即锁账户)、不发 `ForgotPassword`(向真实邮箱发信留痕)、不建用户、不改密。

## 5. 报告必备

结果分级(P0/P1/P2)+ 可粘贴复现命令 + 影响与**边界** + 判负项(信任头绕过 6 组、`/copilot/*` 401、`/copilot/export` 空会话)+ **残留披露**(注册表记录/软标记不可硬删)+ 修复建议(给 `/mcp` 挂同一套 Bearer;健康检查不回显 config;注册表写工具做授权分级;轮换 IdP client secret;关闭开放注册)。
