# 品牌轴反查：从下游应用挖出上游供应商

## 触发
- 目标是**下游买家/白标**：站内功能依赖第三方供货（TG 号源、短信接码、支付通道、卡商、AI 能力）。
- `domain=` / `ip=` 两个轴都无产出（同 IP 没有运维栈，同族站都同一套加固）。

## 四步

### 1. 让应用自己说出上游品牌
- **上游调用的错误体是最短的入口**：服务端把上游原文透传回来，形如
  `<上游名>接口请求失败：{"detail":"product not found"}`；`{"detail":...}` 这种体 = FastAPI（上游是 Python 服务）。
- 同一份上游关系还会出现在：前端 bundle 的集成配置字段（`settings.<vendor>_api_key` 这类“从 <上游> 获取的 API Key”）、
  客服话术里点名的供货方、站内发卡/接码链接的域名、商品表的同步时间（能实时同步 ⇒ 上游连接是活的）。
- 手法：正常调用依赖上游的业务端点，**故意带错参数/错 ID**，读回包里的第三方文案。

### 2. 品牌当测绘关键词
- `body="<品牌中文名>"`、`cert="<品牌>"`、`title="<品牌>"`（FOFA/Censys/ZoomEye，出口走跳板）。
- 实测一发即命中两类资产：上游**公开的 API 文档站**（`<品牌>.example.tld` = Swagger UI）与**同族运维后台**。
- 命中的 IP 段/面板标题要回头做**归属核实**（页面互引同一品牌、同一运营方、同一号源）——归属未证前只读浏览，不外发载荷。

### 3. 上游 API 文档 = 免费契约
- `/openapi.json`（FastAPI，一次拿全路径 + 参数 schema）、`/docs`、`/swagger-ui/index.html`。
- 文档直接写出：鉴权头名与签名要素（HMAC 的 `X-Api-Key/Sign/Timestamp/Nonce`）、端点全集
  （`/products`、`/balance`、`POST /orders`、`/orders/{id}/files/{fileId}`），以及**开通方式** ——
  写明“API 客户由运营总后台人工开通”即无自助注册，别再找注册面。
- 鉴权常是**分层**的（缺头 → `HMAC headers are required`；假签 → `X-Api-Sign format is invalid`）⇒ 错误文案是格式/账号 oracle；
  但**没有 key 就不要原地磨签名算法**。

### 4. 从面板前端反挖同族域
- 面板 SPA HTML 常**免鉴权**（`GET /admin/dashboard` 直出整包前端），下载后 grep：
  `API_BASE`、`http(s)://`、`localStorage` 键名、集成配置字段、页面里“按行粘贴”的示例（常含取号/接码链接模板）。
- 一次得到：同族子域（`link.` 取号站、`admin.` Basic 门户、`fenxiao.` 分销 API）、鉴权机制（HTTPBearer + 2FA）、
  以及该面板**在上游是谁的客户**（设置页写着要填哪家上游的 API Key）。
- 同族各端的鉴权形态差异极大（全局 401/403 / nginx Basic / 免鉴权 OpenAPI）⇒ 逐个实测，别用一台的结论给整族定级。

## 判据与纪律
- **只读优先**：归属未证前不碰写端点，只读 `/openapi.json` 与前端。
- **价值排序**：能导出/接管账号实物（session、tdata、发货文件下载）> 能下单/查余额 > 只能看货架。
- 拿到上游实物后，报告里必须写清**它与主目标的关联证据**，否则只是换了一个不相干目标。
