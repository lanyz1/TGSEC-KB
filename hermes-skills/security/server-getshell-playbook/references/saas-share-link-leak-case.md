# 独角兽SCRM 分享链接数据泄露案例(2026-08-10)

目标: `https://user.dujiaoshouai.com/v2/share/invite/<uuid>`(翻译平台用户管理 / 独角兽SCRM 多租户 SaaS)
后端: `api.dujiaoshou.im`(`/health` = 200,自定义框架 404 页带时间戳)
前端: Vue 3 + element-plus + Vite(主 bundle 1.4MB `/v2/assets/index-*.js`)

## 核心发现链(可复用模式)

### 1. 分享链接 = 公开数据面(最高价值, 免登录)
- 邀请分享页 `requiresAuth:false`(前端路由 meta),打开即自动完成验证流程
- **CDP 打开邀请页 15-20 秒后, localStorage `share_sessions_v1` 自动写入**:
  ```json
  {"tokens":{"<shareId>":"<JWT 625B>"},
   "userInfos":{"<shareId>":{"shareId":"...","shareInvId":"23813","id":11062,
     "username":"<代理邮箱>","expireTime":"2026-09-01","multiAccount":0,"canEditComment":true}}}
  ```
- 提取法: CDP Runtime.evaluate `JSON.parse(localStorage.getItem('share_sessions_v1'))`
- **用 token 调 API**: `getLoginAccountList?invId=<shareId>&page=1&size=50` → **1290 个登录账号全量**(Line 账号/粉丝统计/备注)
- 其他泄露: `share/link/detail`(短链/密码/有效期 2999)、粉丝统计(A=181/B=17829/C=248)

### 2. 前端 JS 挖 API 结构
- 下载主 bundle + 懒加载 chunk(从 bundle 的 `import("./xxx.js")` 提取列表)
- **baseURL 从 axios.create 找**: `rt=un.create({baseURL:"https://api.dujiaoshou.im/admin"})`
- **公开接口 = `/base/open/*` 前缀**(免 token):
  ```
  /base/open/agentLogin       代理登录(需 Altcha)
  /base/open/createAgent      创建代理(公开注册!)
  /base/open/sendEmail        发邮件验证码
  /base/open/resetAgentPwd    重置代理密码(公开!)
  /base/open/googleAuth       Google 认证
  /base/open/altcha/challenge 人机验证(Altcha)
  /base/open/initChannelInfo  渠道配置(含 S3 桶 URL)
  /base/open/chatView         聊天查看
  ```
- **鉴权端点 = `/base/comm/*` + `/v2/*`**(需 Bearer token,无 token 返回 `{"code":1001,"msg":"没有找到 Token"}`)
- 错误码: 1000=成功 / 1001=缺参 / 51=token 空 / 1093=验证失败 / 6000/6008=业务
- 请求拦截器自动加 `Authorization: Bearer` + `Language` 头

### 3. Altcha 人机验证(未破解)
- challenge 返回 `{"parameters":{"algorithm":"PBKDF2/SHA-256","nonce","salt","cost":1500,"keyLength":32,"keyPrefix"},"signature"}`
- **标准 altcha 求解(PBKDF2(nonce,salt,cost) → SHA256 匹配)不匹配** → 自定义封装(keyPrefix 参与签名,构造方式未确定)
- 绕过思路: 用浏览器完成验证(前端有求解代码),或找不需验证的 open 接口

### 4. 管理后台搜索(未突破)
- `admin.dujiaoshouai.com` → nginx 404(无业务)
- `admin.dujiaoshou.im` → 403 Forbidden(存在但拒绝,可能 CF 保护)
- 子域枚举: 仅 user/api/admin/www 存活(DNS 爆破 40 词)
- crt.sh 对这两域名限流(404/502),用 DNS 爆破替代

### 5. 其他泄露
- **S3 桶**: `saasfile.s3.ap-southeast-1.amazonaws.com`(initChannelInfo 返回,多租户 SaaS 共用)
- MQTT: `wss://api.dujiaoshou.im`, 用户名硬编码 `clientadmin`
- 限流: Cloudflare 429 Error 1015(每分钟 ~8 请求触发)→ 用浏览器(cf_clearance cookie)或降频

## 可复用方法论

```
1. 分享/邀请链接 = SaaS 公开数据面: CDP 打开 → 等自动验证 → localStorage 提取 token
2. 前端 bundle 逆向: axios.create baseURL → /open/* 公开接口族 → /comm/* 鉴权接口族
3. 公开注册/重置接口(createAgent/resetAgentPwd)是提权入口
4. 管理后台常是独立域名(admin.xxx), 需子域爆破找
5. Altcha 是自定义封装时, 用浏览器前端求解, 别硬破
```

## 产物
- `D:\博彩通杀\research\dujiao_v2_index.js`(1.4MB 前端全量)
- `dujiao_token.txt`(分享 JWT 625B)
- 脚本: dujiao_recon/dujiao_admin_probe/dujiao_altcha_break 等
