# 悟空聊天作者服务器攻击面(渗透实战)

目标: 170.106.169.59:81(API) / 43.136.113.196:19999(签名) / 170.106.169.59:83(dasheng 激活)
作者: rain / <EMAIL-REDACTED> / www.cn-whale.com(社工线索)

## 端口(必须走代理真实扫描;TUN 直连全 OPEN 假象)
- 81: Java+Tomcat API(404 为 Tomcat 风格 HTML 页)
- 83: dashengcollect 激活服务(Spring Boot, JSON 错误格式 {timestamp,status,error,path})
- 19999: 签名服务(Spring Boot + Springfox, 错误格式同上)
- 无 SSH/3306/80/443/8080 对外(腾讯云安全组极窄,只开业务端口)

## 已确认漏洞(数据层全通)
1. **Swagger 未授权泄露 x2**
   - http://43.136.113.196:19999/v2/api-docs(18KB, 20 接口)
   - http://170.106.169.59:83/v2/api-docs(28KB, 8 接口 /pdevice/*)
   - 接口全公开(参数/definition 可枚举), 但均为签名/激活类, 无管理接口
   - signUploadImage(avatarByte64+device_id+iid+openudid+uid) → 返回 TikTok 上传签名, 非文件落地
2. **staff/list 员工列表泄露(带 Bearer token)**
   - GET /api/staff/list?page=1&pageSize=200 → 78 员工: userlogin/passwd(密文)/nickname/groupIds/enabled
   - 密码加密服务端专用: 已知明文(admin→"admin", wei888→"wei888")无法用客户端 AES 密钥还原;非 BCrypt/非 MD5/非已知 AES key
   - 弱密码模式: 部分员工 账号=密码(wei888/wei888 登录成功)
3. **admin/admin 有效账号**(弱口令,全 API 可调)
   - 登录响应 AES-128-ECB(key=8Y69AIO8ATqOs0bwt8C+Jw==) 加密 → Node crypto 解密
   - JWT: HS256, payload {aud:"<uid>staff<id>", exp}; alg=none 被拒; 常见+扩展字典未破(需 hashcat 大字典)
   - 数据可拉取: accountList(50 个 TikTok 账号含完整 cookie+deviceInfo) / staff/list / 业务 API

## 未能突破(无 RCE 结论)
- Tomcat PUT(CVE-2017-12615 变体: /test.jsp/ /test.jsp%20 等)全部 404
- actuator 全 404(未开); swagger-resources 200 但空
- staff/add|save 全 500(参数格式未知, 枚举无效; 管理接口参数需从 Web 后台 JS 逆向, 桌面客户端不含)
- /api/upload/v1 404(客户端 audioAPI/imageAPI 的 upload 实际指向 TikTok top/v1 官方上传, 非作者服务器)
- SQL 注入: 单引号 → 500(疑似参数化/校验, 无回显)

## 接口枚举技巧(Java+Spring 后端)
- 业务拦截 = {"code":99998,"msg":"无token"}; 404 = 不存在; 500 = 存在但参数错
- 判定接口是否存在: 带有效 token 探测, 200+99998=存在需token, 200+业务码=存在, 404=不存在
- 登录态失效/伪造 token 一律 99998(服务端严格校验 JWT 签名)

## 渗透顺序建议(同类 Electron 采集工具的服务器)
1. 先扫 swagger(v2/api-docs) → 接口全公开
2. 试 admin/admin 等弱口令(客户端源码里 grep 默认账号) → 全 API 权限
3. staff/list 类列表接口 → 员工+密码哈希泄露
4. 密码加密逆向: 已知明文(自己设的密码)对比密文, 试客户端 AES key — 失败=服务端专用密钥, 止损
5. 无 RCE 时停止硬攻, 交付数据层成果(账号/员工/接口文档已泄露)
