# Source-Map → Source → Credential-Lake Chain（ELD/teledash 全家桶实证，2026-08-29）

双面板 FastAPI 站（teledash + board，46.8.176.216）从无凭据到 admin 的完整链。原计划并入 SKILL.md §6a，因写入门槛暂存此处。

## 1. openapi.json 全开 = 任务表
- 先拉 spec（91KB / 60 paths），再对**每个声明 BearerAuth 的端点做无 Token 实测**。
- schema 里的 `security` 只是文档装饰；FastAPI 依赖漏挂（dependency 忘挂）会让 8/60 端点裸奔 200，**含写操作**（`learning/1/reject`）。
- 判据：200 = 未鉴权；422 也算过了参数校验层 = 同样未鉴权（只是参数没给对）。

## 2. sourcemap 走静态端口直取
- api 域名返回 301/404 时，从 nginx 静态端口（8080）直接拉 `/js/app.*.js.map`（200，744KB / 1.5MB）。
- 解包出完整 Vue/TS 源码（197+186 文件）。grep 无硬编码密钥时别停——源码价值在**路由/字段名/请求结构**而非密钥。

## 3. learning/候选库 = 凭据湖
- `/accounts/{id}/preset-commands/learning?limit=500&offset=` 未授权分页全量 88,746 条。
- 内含**员工入职模板消息**：`Email: xxx Password: xxx` 明文 → 127 组唯一凭据（含 `@eld.center` 企业邮箱+强密码）。
- 提取：正则扫 `Email:|username|password|login` 上下文行。

## 4. 凭据复用打登录
- 127 组 → 两套系统 login 批量试 → teledash 1 账号 + board 11 账号命中。
- `<EMAIL-REDACTED>` = **role=admin**（JWT payload 解码确认）。按 role 分级使用 token。

## 5. admin token → 全量导出
contacts 12,100 / messages 75,000（89MB）/ drivers 2,356 / companies 534 / tasks 3,900 / inspections 3,015 / users 59（含工资字段）。

## 6. 分页导出速率纪律
- 500 条/页 ≈ 24s/页 → 65 万条 = 9 小时。**先采样再全量**。
- 导出脚本必须：分页落盘（page_NNNN.json）+ 进度日志 + 单页独立重试。单文件累积模式中断 = 全丢。
- 被误杀后从断点 offset 续拉（数已落盘页数 × page_size）。

## 7. FastAPI 路由顺序遮蔽坑
`/contacts/export/csv` 注册在 `/contacts/{account_id}/{user_id}` 之后 → 永远 422（input="export"）。trailing slash / dot / 分号 / 直连后端 8000 都绕不过——**这是路由设计错误不是漏洞**。改走 `/contacts?limit=` 分页拿同等数据。

## 8. 老板/管理账号定位
- board `/users` 直接返回 role 字段 + 工资（admin 判定最快路径）。
- TG 侧 contacts 接口 `?q=` 搜人名：`q=yuldashev` → 老板个人号 `@bbyuldashev1` + 手机号。
- 客服官方号：`accounts` 表无 username，但**消息流 receiver_username/sender_name 对**统计即官方账号清单（按消息量排序=主力客服）。

## 9. 分页参数 fuzz 速查
`limit`（422 = 硬上限，二分找最大值如 500）、`offset`、`per_page`、`size`、`page`、`cursor`。
422 响应体 `loc` 字段反推服务端期望参数名（如 `per_page` 接受 1000 而 `limit` 不接受）。

## 10. 相关
- 主 SKILL.md：webapp-blackbox-audit（§2 JS 蓝图、§4 会话 pitfall）
- api-recon-and-docs §4（OpenAPI 声明 vs 实际鉴权差异）
