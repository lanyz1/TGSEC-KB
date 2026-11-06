# CORS 优先级守门（cors-vuln-report-priority）

> **永久强制规则**：SRC 黑盒场景下 CORS **不挖、不测、不单独写洞**。

## 原因
- 多数 CORS 配置问题（ACAO 反射、缺 credentials 校验）单独报 = 低危/忽略，纯噪音
- CORS 是**链路基座**，不是主洞：它是帮你打别的洞的跳板（XSS 读接口、跨站带 token），不是目标
- 平台普遍把 CORS 当 N/A/低危，浪费报告配额与时间

## 执行
1. 看到 `Access-Control-Allow-Origin` 反射 → **不测不报**，转注入 / SSRF / XSS / RCE / 越权 / 未授权业务读
2. 文中的 CORS 仅作链路理解（帮助 XSS/CSRF 闭环），禁止把 CORS 单独写成主洞报告
3. 唯一例外：CORS 配合**已发现的存储型 XSS** 构成完整数据窃取链时，作为**辅助链路**写进 XSS 报告中，不独立成篇

## 同类守门
- `vuln-report-format.md`：写不写、怎么定级，只认它
- 报告的结构与定级标准：见 `report-format.md`（8 块结构 + 认钥闸）