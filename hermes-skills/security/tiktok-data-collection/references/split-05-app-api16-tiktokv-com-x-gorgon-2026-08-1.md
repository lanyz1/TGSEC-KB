## ★App 协议（api16 tiktokv.com + X-Gorgon）移植结论（2026-08-19 实测）

- **wukong 的 `algorithm/xGorgon8404.ts`（312 行纯 TS + crypto，零依赖）签名算法可整体移植**：`XGorgon8404.stringToMD5(params)` + `XGorgon84MD5(paramMd5, '', cookieMd5, null)` → `X-Gorgon` + `X-Khronos` 头
- **签名+设备参数验证通过**（用 wukong 样例设备参数 device_id/iid/openudid/cdid/idfv）——App tokenBeat 返回**业务错误 `401 session_expired`** 而非签名错误 = 签名算法正确、设备参数被接受
- **★致命限制：App 协议需要 App 会话**——web cookie（sessionid）在 App 域（api16）不通用，tokenBeat 返回 session_expired；aweme/v1/aweme/post 直接 200 空 body。**别移植 App 协议拿 web 登录账号数据（除非用户能提供 App 会话）**——wukong 的 App 协议只适合它自己 App 登录的账号体系
- 域名：api16-normal-c-useast2a.tiktokv.com（443 HTTPS）；wukong 设备参数样例见 `asar_extracted/electron/api/authAPI.ts:244` 注释（完整 URL 含 iid/did/openudid/cdid）


