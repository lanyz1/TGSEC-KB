## SRC 猎手补充手法

### 云开发匿名 Session 打用户表
- **认什么**：BaaS/云开发（微信云开发、LeanCloud、Supabase）支持匿名登录；前端写死 `appId`+`appKey`/anon JWT；存在低代码数据源函数 `wedaGetRecords` 或 REST `listRows`
- **打法**：不登录，POST 匿名签到拿 JWT（`POST .../sessions/anonymous`），带匿名票打 `sys_user`/业务表 listRows。HTTP 网关返 `LOGIN_TYPE_DISABLED` 别停，换 REST 端点或加 `x-upsert:true` 头。LeanCloud 写死钥直接打 `/1.1/classes/_User`
- **算成**：匿名会话 total 涨；rows 出他人手机/邮箱/报名正文/uin
- **假点**：`_User` 和业务表都 403 ACL 拒绝匿名；只有 app-static 公开静态；无会话也是全表（另一条洞）

### 短链 302 跳转泄露手机号
- **认什么**：业务有短信/运营短链解析站（`/open`、`/app`、`/s/`、`/go/`）；首页是 Hello 壳别停；短码 302 到落地页，query 参数带 `phone`/`mobile`/`name`
- **打法**：不登录，用短字典枚举短码（6-8 位字母数字），跟 302 Location 看 query 参数。`curl -sI https://s.target.com/XXXXX | grep Location`
- **算成**：跳转地址里是别人的 11 位手机/姓名/身份证号
- **假点**：全部是公开营销页无 PII；短码空间太大枚举不到活码

### 自定义身份头当会话（User-Id / X-User-Id）
- **认什么**：管理 SPA 用 `User-Id`/`X-User-Id`/`X-Account` 头当登录身份（微服务网关内部头外露）；前端名单只出数字号不出手机
- **打法**：不登录，从公开列表/接口抄数字用户号，放到 `User-Id` 头打 `/api/me`/`/api/user/info`。`curl -H 'User-Id: 10002' https://admin.target.com/api/me`
- **算成**：回包出他人姓名+11 位手机+邮箱+角色
- **假点**：头被网关剥掉，传了也只回自己的；后端校验 JWT 与头一致

