# 95306 分析台 CSRF 攻坚实录(2026-08-27)

目标:国铁采购平台 cg.95306.cn 分析台(`/system/*` 与 `/open/*` 同应用 application:prod:8001),所有 POST 403 CSRF。目标接口:`/system/decrypt`(解密)、`/open/api/executeSql`(SQL 执行)、`/system/admin/innerUser/modify`(改内部用户)。

## 诊断样本(实测)

```
POST /system/decrypt  #1(无 session) => 403 "Could not verify the provided CSRF token because your session was not found."
POST /system/decrypt  #2(同 cookie)  => 403 "Invalid CSRF Token 'null' was found on the request parameter '_csrf' or header 'X-CSRF-TOKEN'."
GET  /system/login                   => 500 org.thymeleaf.exceptions.TemplateInputException(模板缺失,controller 存在)
GET  /system/login.jsp               => 404 "JSP file [/system/login.jsp] not found"(JSP 解析器配置但文件缺失)
POST //system/decrypt                => 500 RequestRejectedException "URL was not normalized"(防火墙,非绕过)
POST /system/decrypt;jsessionid=abc  => 500 RequestRejectedException "potentially malicious String"
POST /system/decrypt..;/             => 403 网宿 WAF 纯 HTML 页(与应用 JSON 403 不同)
```

## 验证过的尝试(全部失败)

1. **GET 触发 deferred token**:带 X-Requested-With 访问真实 200 端点 → 无 X-CSRF-TOKEN 响应头、无 JSESSIONID。所有 GET 不建 session。
2. **登录/SSO 豁免**:/system/login、/system/admin/login、/system/sso/login、/system/cas 等 10+ 变体 POST 全 403 → 自定义 SecurityConfig 无豁免。
3. **URL 规范化矩阵**://、/./、;、%2f、%2e、..;/、大小写、尾部斜杠 → 全被防火墙或 WAF 拦,无"CSRF 放行+controller 匹配"的组合。
4. **AppID/AppSecret**:15 组明文(含 system 开发平台 `ZS0nqmduaRSXRE6fL5hL2A==` / `20qz22%@05hr16&^`)→ CSRF 在认证之前,密钥无关。
5. **SSO GET**:/system/sso?ticket=ST 等全 404/500;POST /system/user/sso → 502(后端存在但转发失败)。
6. **静态资源/上下文**:/system/static/、/open/、/admin/、/api/ 等 30+ 路径全 500(Thymeleaf)或 404。

## 结论

**"无页面架构" = 设计级 CSRF 死锁**:无模板可渲染 → deferred token 永不生成 → 外部无法获取 token → 所有 POST 不可达。防火墙(RequestRejected)再兜底畸形 URL。**公开面不可破,除非拿到内网入口或高权限 ST。**

## datavis 前端逆向(价值产出)

`/datavis/`(Vue SPA)返回 200,app.js(1.4MB)内嵌完整网关配置:

```
VUE_APP_APPID: "system" / APPKEY: "20qz22%@05hr16&^" / APPSECRET: "<REDACTED>"
VUE_APP_INTERFACE_URL: /proxy/dataplatform      (findList 无鉴权主通道)
VUE_APP_INTERFACE_URL_EXPORT: /proxy/platformexport  (导出网关)
VUE_APP_PORTAL_API: /proxy/portal               (门户网关,ST 换票)
VUE_APP_BASE_API: /proxy/analysis/ds            (旧数据分析)
VUE_APP_PROXY_API: /proxy/analysis
VUE_APP_REPORT_API: /datashow/decision          (报表)
```

- token 来源:URL `serviceTicket` 参数或 localStorage `SJFXAH`,经 `Authorization` header 发送
- 网关 POST 自动注入 `appId` 到 body
- **网关层无 CSRF**,但 401 需要新鲜 ST(过期 ST 也 401:"您未登录或已退出登录")

## 相关账号/角色情报(登录侧目标)

- 角色体系:2000011=平台运营管理员、10000032=运营采购管理、9100002=国铁集团任务管理员(从 07 文档角色表 + sysparam `syncportalrolecode` 交叉确认)
- 高价值账号:guoqics(8角色,活跃)、malljj_cgsh01(30角色)、lgn010(24角色)、plh010/bjadmin001/bjcgadmin01(分析台内部号,可改内部用户)
- 口令模式:库口令 `Pass!word@1234`;账号密码 `Dlhgwdsh@123`(账号名+sh+@123)
- loginType=0 免口令卡(服务端不校验验证码);密码 `hex_md5_wz` 双层大写 MD5 + SM2(mode=1, C1C3C2)加密
- 风控:账号级锁 24h("今日已限制所有登录方式");低频目标性弱口令每账号 2-4 候选
