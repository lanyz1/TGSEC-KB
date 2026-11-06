# PHP 老后端:请求编码前提 + 认证端点三件套实测 + 长扫描落盘纪律

来源:9v111 / A7777bet(`game-service.9v.com` → 源站 45.13.59.23,Host 头直连绕 CF)2026-09 实测。
配套阅读:`references/dto-whitelist-and-route-inventory.md`(同目标的前一轮:DTO 白名单族 / 参数名 oracle / 405 反推路由)。

---

## 1. 请求编码前提:JSON 被静默忽略,害我白扫一整轮

老 PHP 后端(Laravel 里直接读 `$_POST`、传统框架)**静默忽略 JSON body**,只认
`application/x-www-form-urlencoded`。报错极具误导性 —— 服务端回
`"Telefone e senha são obrigatórios"` / `"X is required"`,看起来**像是字段名猜错了**,
于是我整轮去换 `mobile / phone / telefone / phoneNumber / passWord / password`……
**字段名一直是对的,错的是编码。**

判定法(两个请求定死):
```
同一路由 → application/json        → "X 是必填" / 字段读不到
同一路由 → x-www-form-urlencoded   → 真正的业务校验(如 "Telefone ou senha inválidos")
⇒ 编码才是问题,字段名本来就对
```

实测契约:
- 登录:`POST /api/user/phoneLogin` 字段 = **`phoneNumber` + `passWord`(注意大写 W)**,**必须 form-urlencoded**;JSON 提交永远只回 `"Telefone e senha são obrigatórios"`。
- 注册:`POST /api/user/phoneRegister` 同样只在表单编码下才真正创建账号。
- 惯例:登录 / 注册 / 改密 / 绑卡等**写接口优先 form-urlencoded**;读接口 GET query 通常两种都认。

**通用教训**:遇到"必填字段"报错,**先怀疑编码,再怀疑字段名**。换字段名是下策;换编码是一次性的高赔率动作。

---

## 2. 认证端点三件套:实测结论(可直接复用的负面/正面判据)

| 端点 | 测试 | 结论 |
|---|---|---|
| `phoneLogin` | 表单编码 + 正确字段名 | 真校验凭证 → 成功回 `data.accessToken` |
| `phoneRegister` | **无需 SMS / 邮箱验证即注册成功**并直接发 token | ⚠️ **真实缺陷**:可无限养号(刷首充/试用金/邀请返利) |
| `phoneRegister` 重复号码 | 回 `{"code":"1002","msg":"Telefone já cadastrado"}` | 去重正确 → **不构成 ATO**;但差异化响应 = **手机号存在性 oracle** |
| `reloadToken` | 传 `{}` / `{id:1}` / `{mobile:<他人>}` / `{user_id:1}` | **一律只返回自己的 token**,参数被忽略 |
| `reloadToken` 无 Authorization | — | `{"code":"8888","msg":"用户身份失效,请重新登录!"}` → 鉴权强制,**不能代签他人 token** |

关键认识:**"看起来能签发 token"的端点(名如 reloadToken / refreshToken / getToken)必须实测**,不要因为它名字危险就跳过、也不要因为它是 token 端点就假定能越权 —— 这里两次都是负结果。

## 3. Token 生命周期与跨会话复用(省钱动作)

- 本平台 token = **64 位 hex**,`expiresIn: 2592000` = **30 天**。
- **跨会话先重测旧 token**:本轮上个月抓到的 token 仍然有效,直接拿到有效认证会话,**省掉重新登录/注册**。手上任何历史 token 先花一个请求验活,再决定是否重新取。
- 验活方式:`GET /api/user/getUserInfo` 带 `Authorization: Bearer <tok>` → `code:0000` + `data.id` 即活。

## 4. 调试模式探测:用类型混淆触发 500,一次判定 APP_DEBUG

不要靠猜 `/.env`、`/_ignition/health-check` 的 404/403(那些只说明静态屏蔽)。
**真正的判据是"能否把应用打到 500"**,再在响应里找 `APP_DEBUG / APP_KEY / ignition / whoops / Stack trace / SQLSTATE`:

```python
# 类型混淆 / 畸形输入,逐个打
{'page': []}          # 数组给标量
{'page': {'a': 1}}    # 对象给标量
'{bad json'           # 坏 JSON
{'phoneNumber': {'a': 1}}   # 嵌套给字符串字段
'/api/user/getUserInfo/x/y/z'   # 多余路径段
```
实测结果:全部返回**参数校验错误**,无 500、无 stack trace、无 env 输出
⇒ **该主机 APP_DEBUG=off**(此前记录的"源站同机 APP_DEBUG"已证伪,勿再引用)。

反过来说:**接口对畸形输入全部优雅报错 = 加固良好的信号**,可以据此停止在"调试泄露"这条线上继续投入时间。

## 5. 长扫描落盘纪律(踩过两次,务必遵守)

远端 `timeout` 杀掉进程时,`python xxx.py | tail -N` 的 **stdout 会整段丢失** —— 实测丢掉过
两轮 270 组合矩阵的结果,只能重跑。

规矩:
1. 脚本内 `L=[]` + `W()` 同时 `print` 和 `append`,**结尾一次性写 `/tmp/xxx.out`**;
   更稳的是**增量 append 落盘**,这样中途崩溃也留得住部分结果。
2. 解析后统一 `jget('/tmp/xxx.out','xxx.out')` 取回本地再读 —— 不要依赖 SSH stdout。
3. **脚本自身的收尾也要 try/except 兜住**:本轮 helper 参数写错(`W() takes 1 positional
   argument but 3 were given`)在最后一步崩掉,导致结果文件根本没生成,整轮白跑。
   收尾写文件这件事必须放在会崩的逻辑之前,或单独 try 包住。
4. 同理适用:`timeout` 值给足,但**不要用 `| tail` 缩短远端输出** —— 它既丢信息,又让退出码
   变成 tail 的 0,掩盖真实失败。

## 6. 本轮目标侧的总判读(便于下次直接接续)

`9v111` 玩家 API 从**数据提取**角度已确认加固:DTO 白名单 + token 作用域严格,查询类一律只返本人;
`reloadToken` 不能代签;无 APP_DEBUG 泄露;未授权面只有站点配置/游戏清单/公告(无 PII)。
**唯一剩余出口 = Filament 管理后台**(`a7777bet.top/admin/login` 与 `game-service.9v.com/admin/login`
同页,45KB 活登录页;`/admin` 根为自定义 404 `{"code":"404","msg":"404 - Interface não existe"}`;
`/admin/password-reset/request`、`/admin/logout` 均 404 未启用)。**该出口需凭据,用户明确禁止爆破。**
