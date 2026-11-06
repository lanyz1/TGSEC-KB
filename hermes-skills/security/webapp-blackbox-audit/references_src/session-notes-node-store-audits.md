# Session Notes: Node/Express 黑盒审计三案例 (2026-08)

## 用户透明工作流偏好（SKILL 级约束）
用户明确要求：每步探测**先说明做什么/为什么 → 再执行 → 贴关键原始输出 → 后总结**。
不要只给提炼结论；工具原始日志的关键行要直接展示。已同时存入 memory。

## 案例要点速查

### tgpool 控制台 (www.nini77.com)
- FastAPI + Vue3，Cloudflare 代理；openapi.json 公开 85 端点
- 认证 X-API-Token / Bearer JWT；94 受保护端点全部正确 401
- 域名历史（Wayback）：2011-2017 是韩语博彩站——域名污点是运营风险项
- 登录时间侧信道：admin 波动大(0.43-1.95s) vs 不存在用户稳定

### 讯飞号铺 (47.237.1.86 / facebook996.com)
- Express 发卡商店；注册表单必填 `contact` 字段，确认密码字段名 `passwordConfirm`
- 支付单归属隔离验证法：账号 B 查账号 A 的支付单 → 404 PAYMENT_NOT_FOUND = 有隔离
- 充值金额校验严格（0/-100/0.01/1e9 全 400 BAD_AMOUNT）；支付走第三方 yf.yuckk.cn
- 注册接口用户名枚举：已存在返回 409「该用户名已被使用」

### CCNOW AI 面板 (43.156.227.212 / xtoylover.cloud)
- 单用户模式（multiUserEnabled:false）→ 一个口令=整个防线，无限流=高危
- Vite dev server ×3 公网（7719-7722）：/@vite/client 可访问确认 dev 模式；/@fs 已限制（新版已补丁）
- File Browser v2.62.1：配置 JSON 直接嵌在 HTML 里（window.FileBrowser）
- 高位端口必须扫：组件藏在 77xx

## 工具坑位
- http.cookiejar 不跨进程持久化：login+测试必须同一脚本内完成
- 自建 sess.py helper（mkop/req），req() 默认 GET，POST 必须显式传 method
- crt.sh 经常 502/404，备选 Google DoH + socket 批量解析
