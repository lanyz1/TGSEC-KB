## 5. nginx 403 ≠ 接口不可达(路径级访问控制绕过)

- 目录页(`/legacy/`、`/douxingbang/`)403 常只挡静态/HTML 入口;**真实框架入口 `public/index.php`(ThinkPHP)可能直接 200**。
- 403 后先试:框架入口文件、`?s=/api/controller/action` 兼容路由(登录/注册表单常可 POST);再试路径编码/大小写/IP+Host 直连/XFF 伪造/UA 伪装/HTTP/1.0。WAF 挡"机房 IP 访问目录页"时 API 入口往往裸奔。
- 老活动/打榜/投票类 TP 站(index/user/login.html、api/sms/send、api/user/login)常有**独立用户库**,可测主账号能否直接登老系统(同库判定:同一手机号+密码双站可登 = 同库,重大发现)。

