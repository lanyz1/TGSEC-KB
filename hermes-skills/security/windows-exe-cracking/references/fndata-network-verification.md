# fndata 网络验证平台协议(轻云3.8 实测)

fndata 是国内常见网络验证 SDK(类似飞鸟/易游验证),服务端为 Go 写的 HTTP API。
轻云3.8(PUBG 自动打药辅助)用它做卡密/账号验证。以下为该平台的完整协议画像,
适用于任何使用 fndata 系列 SDK 的目标。

## 服务器结构

```
API 端点: http://<ip>:18888/Api?AppId=<appid>
备用域名: 常同时硬编码一个域名(如 pubg.795999.xyz:18888)
AppId:    每个"版本"一个(轻云3.8 有 10013=测试版 / 10015=代理版 / 10016=普通版)
传输:     HTTP(非 HTTPS!端口 18888)
```

## 硬编码凭证(main.dll 中,紧邻 API URL 字符串)

从 `http://101.35.246.71:18888/Api?AppId=10013` 附近的 4-8KB 字符串区一次挖齐:

| 凭证 | 示例值(轻云3.8) | 用途 |
|---|---|---|
| `Token` 头 | `ST7UUAN0HTDQAUUVJZBED42LBNBYNK80` | 请求头 `Token:` |
| `KEY` 头 | `Szl137976` | 请求头 `KEY:` |
| AES 密钥 | `sDxmQP644fafnDK3tGZnFBjA`(24字节) | 请求体加密(aes_key) |
| RSA 公钥 | `-----BEGIN PUBLIC KEY-----` 1024位 PEM,每 AppId 一套 | 加密 AES 密钥 |
| 请求头模板 | `Accept`, `Accept-Language: zh-CN`, `Content-Type: application/json`, `User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64)` | 每请求携带 |

## API 函数(从字符串/文档串还原)

- `UserLogin` — 参数 `User`/`PassWord`/`UserOrKa`(账号或卡号)/`Tab`/`AppVer`/`gddd`
- `Register` — `User`/`PassWord`/`SuperPassWord`/`Qq`/`Email`/`Phone`
- `HeartBeat` — `Token`(心跳续期,到期自动关程序)
- `LogOut` — `TOKEN`
- `GetKaInfo` — `Ka`(卡号详情)
- `SetUserClass` — `Mark`(转换用户类型)
- `GetAppUserInfo` — 获取当前用户信息

## 响应结构(JSON)

```
错误:  {"Time": <unix>, "Status": 106, "Msg": "Token无效"}
成功:  含 Token / Key / LoginIp / LoginTime / OutUser / RegisterTime /
       UserClassMark / UserClassName / VipNumber / VipTime / NewAppUser
```

Status 码:106 = Token 无效;其他码表需从 DLL 中文串挖。

## 加密流程(混合加密)

1. 请求体 JSON 用 **AES**(密钥=aes_key 字段,模式 ECB/CBC 需从代码确认)加密
2. AES 密钥再用 **RSA 公钥**加密(每 AppId 一套公钥)
3. 请求头带明文 `Token:` 和 `KEY:`
4. 响应:服务器用私钥加密的数据,客户端用公钥"解密"(特殊操作,见 `公钥解密` 字符串)

## 服务端指纹

- GET `/Api` 返回 Go 风格 `404 page not found`
- POST + 空体 + 头 → `{"Status":106,"Msg":"Token无效"}` 证明服务器活且校验头
- 端口 18888 常用;端口扫描时 80/443/8080/8888 全开可能是反代/WAF 入口,真正 API 在 18888

## 本地状态文件

登录成功后程序写:
- `C:\JLA\login_prefs.json` / `dashboard_prefs.json` / `user_prefs.json`(登录偏好)
- `C:\Windows\winS` / `winSS`(登录状态标记)

## 绕过要点

- 验证服务器 IP+全部加密凭证硬编码在客户端 → 可完整复刻协议直接调 API(注册机/模拟登录)
- 或 hosts 劫持 + 本地 Flask 模拟服务器(需实现 RSA/AES 解密响应)
- 或 Frida hook `UserLogin`/`HeartBeat` 函数改返回值(最省事)
