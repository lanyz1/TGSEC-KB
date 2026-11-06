# 太公望 v42/v52 — 面板无 session 导出面（2026-09-05 实测）

家族: 太公望-骚公云控（136.0.10.86 测试站 v42 / 108.165.255.144 生产站 v52.50, tg.91taigongwang.com）

## 导出面判定
- **v42**（:8000, FastAPI/uvicorn）: openapi.json 全暴露（51 路径/240 端点），**零 export/download/backup/dump 类路径**；`/api/import*`、`/api/runtime/accounts`、`/api/import/failures/{token}` 全部被守卫拦
- **v52.50**（:443 生产）: openapi 本身 401 → 改用前端 JS 提取 API 路径做替代地图：`re.findall(r'[`\'"](/api/[^`\'"]*)[`\'"]', js)` 模板串感知正则，实测 73 条，同样零导出路径；登录限速 3 次/60s
- session 落主机磁盘（与 telegram-manager 家族同款）→ **取得唯一路径 = 主机 RCE**（归入导出矩阵「RCE-only」档）

## 守卫结构（v42）
- `ADMIN_PASSWORD/APP_SECRET` 未配置 → 守卫 503 `{"detail":"服务器尚未配置安全参数"}` 在**端点内部**执行
- 矩阵分类法：**422 = 参数校验层可抵 handler**（import/import/batch/auth/send-code 等写端点都在此档）；**503 = 守卫拦截**；200 仅 `/`、`/api/version`、`/api/logout`
- 结论：守卫不是漏挂型（每端点内部自检），修好配置即全端点激活——死面但无越权面

## 其他面
- WS `/ws` 与商城 `/ws/chat/{id}`：子协议鉴权 `auth.{admin_token}` / `visitor.{visitor_key}`；裸 socket 复刻握手才见真值（101=对 key / 403=错 key）；v52 `/ws` 无 query/子协议/cookie token 通道 = nginx 会话锁
- 坑：FOFA 索引报 108:8000 开放 = **陈旧记录**，TCP 直连 refused 定性
- 商城同机 443（SNI ovigold.com）有独立的客户级商城（Vue3），与云控面板完全分离（独立 JWT secret，token 不互认）

## 家族横向对照
- telegram-manager 家族（gotd/Go）：同样 session 仅磁盘无 HTTP 出口 → 两家同为 RCE-only
- 差异：太公望守卫在端点内（配置缺失全瘫），telegram-manager 老版全 API 无认证（直通）——同源码不同代际部署姿势不同
