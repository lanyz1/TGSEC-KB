<!-- archived from /root/.hermes/skills/security/reset-token-disclosure-ato/SKILL.md on 2026-10-21 -->

---
name: reset-token-disclosure-ato
description: "找密接口回显 reset_token → 未授权账号接管(ATO)。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/reset-token-disclosure-ato`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/reset-token-disclosure-ato/…')`，不要相对 `references/legacy/` 解析。

# 找密令牌泄漏 → 未授权账号接管(ATO)

触发: 忘记密码 / forgot-password / reset_token / 口令重置 / 账号接管 / 邮箱枚举 场景下使用。

## 触发条件
- 已确认登录协议,但登录面无法突破(无口令、禁爆破)
- 站点有「忘记密码 / 找回密码 / forgot password」入口
- 后端返回 JSON(自研 API、FastAPI、Laravel、Spring) —— **前端 SPA 常把 token 直接塞进响应体**

## 核心判据(30 秒定性)
对**自己账号**调忘记密码,把**完整响应体**打印出来看有没有 `reset_token` / `token` / `resetLink`:

```bash
curl -sk -X POST https://TARGET/api/auth/forgot-password \
  -H 'Content-Type: application/json' -d '{"email":"自己的邮箱"}'
```
- 响应体出现任何 32/64 位随机串 → **令牌泄漏,直通 ATO**
- 只有「已发送邮件」文案 → 走邮箱 oracle(见下)
- ⚠️ 只看 HTTP 200 不够,必须打印 body;自研后端常把 token 放在 `data.reset_token`

## 步骤
1. **确认泄漏**:自己账号 forgot → 拿到 `reset_token`
2. **存在性 oracle**:对**不存在的邮箱**再调一次
   - 真邮箱 → 回 `reset_token` / `Token gerado com sucesso`
   - 假邮箱 → 通用文案 `Se o email existir...` 且**无 token**
   → 二者可区分 = 邮箱枚举 oracle(报告里单独列一条)
3. **打通链路(先用自己的账号,零影响)**
   ```
   forgot(自己) → reset_token → POST /reset-password {token,new_password} → login(新口令) → 新 access_token 打 /me
   ```
   拿到 `/me` 200 才算实证;顺手验证 token 单次有效(复用应 400)
4. **字段名先查规范**:FastAPI 站点先 `GET /openapi.json`(常裸暴露),再试 `/docs`、`/redoc`。从 schema 读 `ResetPasswordRequest` 的**确切字段名**,别猜
5. **定向找高权账号邮箱**(低量、1~2s 间隔、oracle 驱动,**非爆破**):
   - OSINT 优先级:应用商店/Play 商店页信息、官网 Footer、LinkedIn、GitHub commit author、LGPD/隐私政策页
   - 常见候选:admin@ / suporte@ / administrador@ / contato@ / ti@ / financeiro@ / dev@ / gestor@
   - 用步骤 2 的 oracle 逐个确认真伪
6. **接管后先看角色** —— 常见坑:种子账号角色只是普通用户/coordinator,数据接口仍 403
7. **验证 RBAC 是不是真拦**(别把 403 当成功):
   - 列全量:`GET /users`、`/account-info/all`、`/partners`
   - **自改角色提权**:`PUT /users/{自己的id}` body `{"role":"administrator"}` → 若 200 且 `/me` 变 administrator = 直达全量数据
   - 变体:`PATCH`、`POST /users {"role":"administrator"}`、`{"is_blocked":false,"active":true}`

## 陷阱
- **响应 token 层级**:常见 `{"data":{"access_token":...}}`,平铺取 `json()['access_token']` 会拿不到 → 打印全文定层级
- **405/404 都是假的**:Laravel 未知路径 POST 也回 405;Symfony 默认错误页 1011 字节;判断路由存在要看响应体特征
- **注册的 role 字段被忽略**:register 传 `role=administrator` 多数被后端丢弃,固定给最低角色
- **QA/测试环境播种真实员工邮箱**:QA 库常只有 coordinator 测试号,没有 administrator → 全量数据取不到,**如实标注**
- **口令重置不可逆**:改了就还原不了原口令,属必须写进报告的痕迹;用户偏好无痕时优先只读取证、不新建超管账号
- **生产 vs QA**:同代码库则生产大概率同款,但持牌机构/真实员工生产环境的 ATO 属重大动作 —— 先报告,等明确授权

## 实战案例(2026-09-12, Treeal Backoffice QA)
`backoffice-qa.treeal.com`(FastAPI + Keycloak 认证的巴西支付后台):
- `POST /v3/auth/forgot-password` **无鉴权回显** `data.reset_token`(30 分钟、单次有效)
- `POST /v3/auth/reset-password` 无鉴权 → 改口令 → `/v3/auth/login` 拿 token
- 实证接管 3 个账号:自注册 1 个 + 真实账号 `<EMAIL-REDACTED>`、`<EMAIL-REDACTED>`(均由 Play 商店页 OSINT 发现,角色均 **coordinator**)
- `GET /openapi.json` 裸暴露 17 条路由 + 角色枚举(administrator/coordinator)
- RBAC 正确:coordinator 打 `/v3/users`、`/v3/payment-panel/account-info/all`、`/v3/partners` 全 403;`PUT /v3/users/{自己}` 改 role 亦 403 → **ATO 成立但未取得全量数据**(需 administrator 邮箱,QA 无此账号)

## 报告要点
令牌泄漏(无鉴权)+ 邮箱 oracle 两条独立漏洞;附可复制复现命令;影响账号清单与口令变更(不可恢复)必须写进「痕迹与恢复」章节;修复建议:响应体移除 token、统一真/假邮箱文案、生产与 QA 都关闭 openapi.json。
